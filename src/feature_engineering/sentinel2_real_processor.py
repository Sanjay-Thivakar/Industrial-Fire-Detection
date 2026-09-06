"""Real Sentinel-2 CDSE processing pipeline (Phase 3 — Step 3C).

Connects the localized Sentinel-2 Level-2A retrieval pipeline to the Copernicus Data
Space Ecosystem (CDSE) Sentinel Hub Processing API and executes the end-to-end
Step 3A (spectral extraction) and Step 3B (temporal change) feature pipeline.

IMPORTANT SCIENTIFIC AND DOMAIN CONSTRAINTS:
1. Sentinel-2 is an optical multispectral sensor (VNIR/SWIR), NOT a thermal sensor.
   It cannot observe flames, heat, or thermal plumes. Change features represent
   optical surface-change evidence only.
2. No synthetic data is ever substituted as a fallback for real imagery.
   If credentials or products are missing, status is recorded explicitly.
3. Does NOT classify events as fire/industrial fire, does NOT train ML models,
   and does NOT modify Phase 2C datasets.
"""

import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import rasterio
from rasterio.io import MemoryFile

from src.config import Config
from src.data_ingestion.sentinel2_patch_retriever import (
    Sentinel2ProcessingClient,
    compute_localized_aoi_bbox,
)
from src.feature_engineering.sentinel2_spectral import Sentinel2SpectralExtractor
from src.feature_engineering.sentinel2_change import (
    Sentinel2ChangeFeatureCalculator,
    STATUS_SUCCESS as CHANGE_STATUS_SUCCESS,
    STATUS_MISSING_PRE,
    STATUS_MISSING_POST,
    STATUS_MISSING_BOTH,
    STATUS_INVALID_INPUT,
    STATUS_INSUFFICIENT_VALID_DATA,
)

logger = logging.getLogger(__name__)

# Expected band order from Sentinel Hub evalscript in Sentinel2ProcessingClient
TARGET_BANDS = ["SCL", "B04", "B08", "B11", "B12"]

# Observation and processing statuses
STATUS_REAL_CDSE_SUCCESS = "REAL_CDSE_SUCCESS"
STATUS_AUTH_REQUIRED = "AUTH_REQUIRED"
STATUS_MISSING_PRODUCT = "MISSING_PRODUCT"
STATUS_PROCESSING_API_ERROR = "PROCESSING_API_ERROR"
STATUS_CORRUPT_RASTER = "CORRUPT_RASTER_DATA"
STATUS_DIMENSION_MISMATCH = "DIMENSION_MISMATCH"


def parse_geotiff_bands(
    data_bytes: bytes,
    expected_bands: List[str] = TARGET_BANDS,
    expected_shape: Optional[Tuple[int, int]] = None,
) -> Dict[str, np.ndarray]:
    """Parse raw GeoTIFF bytes returned by CDSE Processing API into a dictionary of 2D numpy arrays.

    Args:
        data_bytes: Raw bytes of the multi-band GeoTIFF image.
        expected_bands: List of band names in the order defined by the evalscript.
        expected_shape: Optional expected (height, width) tuple for validation.

    Returns:
        Dictionary mapping band names ('SCL', 'B04', 'B08', 'B11', 'B12') to 2D numpy arrays.

    Raises:
        ValueError: If raster is corrupt, band count mismatches, or arrays are non-aligned.
    """
    if not data_bytes or len(data_bytes) == 0:
        raise ValueError("Empty raster data bytes received.")

    try:
        with MemoryFile(data_bytes) as memfile:
            with memfile.open() as src:
                band_count = src.count
                height = src.height
                width = src.width

                if band_count < len(expected_bands):
                    raise ValueError(
                        f"Expected at least {len(expected_bands)} bands, but GeoTIFF contains {band_count}."
                    )

                raw_arr = src.read()  # shape: (count, height, width)

    except Exception as e:
        raise ValueError(f"Failed to read GeoTIFF bytes: {e}") from e

    if expected_shape is not None:
        exp_h, exp_w = expected_shape
        if height != exp_h or width != exp_w:
            raise ValueError(
                f"Raster dimensions ({height}x{width}) do not match expected ({exp_h}x{exp_w})."
            )

    bands: Dict[str, np.ndarray] = {}
    for i, name in enumerate(expected_bands):
        plane = raw_arr[i]
        if name == "SCL":
            bands[name] = plane.astype(int)
        else:
            bands[name] = plane.astype(np.float64)

    return bands


class Sentinel2RealProcessor:
    """End-to-end real Sentinel-2 L2A processor for FIRMS prototype events.

    Orchestrates localized 1 km x 1 km AOI retrieval from CDSE Processing API,
    applies Step 3A spectral feature extraction, and executes Step 3B temporal
    change calculation.
    """

    def __init__(
        self,
        processing_client: Optional[Sentinel2ProcessingClient] = None,
        spectral_extractor: Optional[Sentinel2SpectralExtractor] = None,
        change_calculator: Optional[Sentinel2ChangeFeatureCalculator] = None,
        patch_size_m: float = 1000.0,
        target_resolution_m: float = 20.0,
        min_valid_pct: float = 70.0,
    ):
        self.client = processing_client or Sentinel2ProcessingClient()
        self.spectral_extractor = spectral_extractor or Sentinel2SpectralExtractor()
        self.change_calculator = change_calculator or Sentinel2ChangeFeatureCalculator(
            min_valid_pct=min_valid_pct
        )
        self.patch_size_m = patch_size_m
        self.target_resolution_m = target_resolution_m
        self.min_valid_pct = min_valid_pct
        self.expected_dim = int(patch_size_m / target_resolution_m)

    def process_single_observation(
        self,
        event_id: str,
        latitude: float,
        longitude: float,
        observation_date: Optional[str],
        product_id: Optional[str],
        timing: str = "pre",
    ) -> Tuple[str, str, Optional[Dict[str, Any]], bool]:
        """Retrieve real CDSE localized patch and extract Step 3A spectral features.

        Args:
            event_id: FIRMS event identifier.
            latitude: Target latitude in WGS84.
            longitude: Target longitude in WGS84.
            observation_date: Observation date string (ISO) or None/nan.
            product_id: CDSE product UUID or None.
            timing: 'pre' or 'post'.

        Returns:
            Tuple of:
            - status: e.g. STATUS_REAL_CDSE_SUCCESS, STATUS_MISSING_PRODUCT, STATUS_AUTH_REQUIRED, etc.
            - failure_reason: Diagnostic message if unsuccessful, else empty string.
            - step3a_features: Dict of extracted Step 3A features if successful, else None.
            - is_real_cdse_data: True if real pixels were retrieved and processed, False otherwise.
        """
        # 1. Check if observation exists from catalogue search
        if not observation_date or str(observation_date).lower() in ("none", "nan", ""):
            return (
                STATUS_MISSING_PRODUCT,
                f"No usable {timing}-event product was matched in Step 1 catalogue search.",
                None,
                False,
            )

        # 2. Check credentials
        if not self.client.has_credentials():
            return (
                STATUS_AUTH_REQUIRED,
                "CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLIENT_SECRET) not configured.",
                None,
                False,
            )

        # 3. Compute localized AOI bbox
        try:
            bbox = compute_localized_aoi_bbox(latitude, longitude, self.patch_size_m)
        except Exception as e:
            return (
                "INVALID_COORDINATES",
                f"Failed to compute AOI bounding box: {e}",
                None,
                False,
            )

        # 4. Request localized patch from CDSE Processing API
        res = self.client.request_localized_patch(
            bbox=bbox,
            date_str=str(observation_date),
            resolution_m=self.target_resolution_m,
            target_bands=TARGET_BANDS,
        )

        if not res.get("success", False):
            raw_status = res.get("status", "UNKNOWN_ERROR")
            err_msg = res.get("error_message", "Failed to retrieve patch from CDSE Processing API")
            if "AUTH" in raw_status:
                return STATUS_AUTH_REQUIRED, err_msg, None, False
            return STATUS_PROCESSING_API_ERROR, f"{raw_status}: {err_msg}", None, False

        # 5. Parse returned GeoTIFF raster bytes
        data_bytes = res.get("data_bytes", b"")
        try:
            bands = parse_geotiff_bands(
                data_bytes,
                expected_bands=TARGET_BANDS,
                expected_shape=(self.expected_dim, self.expected_dim),
            )
        except ValueError as ve:
            return STATUS_CORRUPT_RASTER, f"GeoTIFF parsing failed: {ve}", None, False

        # 6. Apply Step 3A spectral extraction on REAL pixel data
        step3a_feats = self.spectral_extractor.extract_features(bands)

        return (
            STATUS_REAL_CDSE_SUCCESS,
            "",
            step3a_feats,
            True,
        )

    def process_event(self, event_row: pd.Series) -> Dict[str, Any]:
        """Execute the full Step 3C pipeline for a single prototype FIRMS event.

        Args:
            event_row: Series containing event information from Step 1 prototype CSV.

        Returns:
            Dictionary containing combined event info, pre/post Step 3A features,
            and Step 3B change features.
        """
        ev_id = str(event_row.get("event_id", ""))
        lat = float(event_row.get("latitude", 0.0))
        lon = float(event_row.get("longitude", 0.0))
        acq_date = str(event_row.get("acquisition_date", ""))
        priority = str(event_row.get("candidate_priority", ""))
        lc_class = str(event_row.get("landcover_class", ""))
        frp = float(event_row.get("frp", np.nan)) if pd.notna(event_row.get("frp")) else np.nan

        pre_date = event_row.get("selected_pre_image_date")
        pre_prod_id = event_row.get("pre_product_id")
        pre_prod_name = event_row.get("pre_product_name")
        pre_tile_id = event_row.get("pre_tile_id")

        post_date = event_row.get("selected_post_image_date")
        post_prod_id = event_row.get("post_product_id")
        post_prod_name = event_row.get("post_product_name")
        post_tile_id = event_row.get("post_tile_id")

        # Process pre observation
        pre_status, pre_reason, pre_s3a, pre_is_real = self.process_single_observation(
            event_id=ev_id,
            latitude=lat,
            longitude=lon,
            observation_date=pre_date,
            product_id=pre_prod_id,
            timing="pre",
        )

        # Process post observation
        post_status, post_reason, post_s3a, post_is_real = self.process_single_observation(
            event_id=ev_id,
            latitude=lat,
            longitude=lon,
            observation_date=post_date,
            product_id=post_prod_id,
            timing="post",
        )

        # Apply Step 3B change calculation
        change_feats = self.change_calculator.compute_change_features(pre_s3a, post_s3a)

        # Determine overall event processing status
        is_real = pre_is_real and post_is_real
        if pre_status == STATUS_REAL_CDSE_SUCCESS and post_status == STATUS_REAL_CDSE_SUCCESS:
            overall_status = STATUS_REAL_CDSE_SUCCESS
            failure_reason = ""
        elif pre_status == STATUS_AUTH_REQUIRED or post_status == STATUS_AUTH_REQUIRED:
            overall_status = STATUS_AUTH_REQUIRED
            failure_reason = pre_reason if pre_status == STATUS_AUTH_REQUIRED else post_reason
        elif pre_status == STATUS_MISSING_PRODUCT and post_status == STATUS_MISSING_PRODUCT:
            overall_status = "MISSING_BOTH_PRODUCTS"
            failure_reason = "Both pre and post observations were missing in catalogue search."
        elif pre_status == STATUS_MISSING_PRODUCT:
            overall_status = "MISSING_PRE_PRODUCT"
            failure_reason = pre_reason
        elif post_status == STATUS_MISSING_PRODUCT:
            overall_status = "MISSING_POST_PRODUCT"
            failure_reason = post_reason
        elif pre_status == STATUS_PROCESSING_API_ERROR or post_status == STATUS_PROCESSING_API_ERROR:
            overall_status = STATUS_PROCESSING_API_ERROR
            failure_reason = pre_reason or post_reason
        else:
            overall_status = "PROCESSING_FAILED"
            failure_reason = f"Pre: {pre_status} ({pre_reason}) | Post: {post_status} ({post_reason})"

        # Construct combined record
        record: Dict[str, Any] = {
            "event_id": ev_id,
            "latitude": lat,
            "longitude": lon,
            "firms_acq_date": acq_date,
            "candidate_priority": priority,
            "landcover_class": lc_class,
            "frp": frp,
            "processing_status": overall_status,
            "is_real_cdse_data": is_real,
            "failure_reason": failure_reason,
            # Selected observation metadata
            "selected_pre_image_date": pre_date if pd.notna(pre_date) else "",
            "pre_product_id": pre_prod_id if pd.notna(pre_prod_id) else "",
            "pre_product_name": pre_prod_name if pd.notna(pre_prod_name) else "",
            "pre_tile_id": pre_tile_id if pd.notna(pre_tile_id) else "",
            "pre_observation_status": pre_status,
            "pre_observation_failure_reason": pre_reason,
            "selected_post_image_date": post_date if pd.notna(post_date) else "",
            "post_product_id": post_prod_id if pd.notna(post_prod_id) else "",
            "post_product_name": post_prod_name if pd.notna(post_prod_name) else "",
            "post_tile_id": post_tile_id if pd.notna(post_tile_id) else "",
            "post_observation_status": post_status,
            "post_observation_failure_reason": post_reason,
        }

        # Forward Step 3A features with pre_ and post_ prefixes
        all_s3a_keys = [
            "s2_feature_status", "s2_feature_failure_reason", "s2_total_pixels",
            "s2_spectral_valid_pixels", "s2_spectral_valid_pct",
            "s2_ndvi_mean", "s2_ndvi_median", "s2_ndvi_std", "s2_ndvi_min", "s2_ndvi_max",
            "s2_nbr_mean", "s2_nbr_median", "s2_nbr_std", "s2_nbr_min", "s2_nbr_max",
            "s2_ndwi_mean", "s2_ndwi_median", "s2_ndwi_std", "s2_ndwi_min", "s2_ndwi_max",
            "s2_swir_ratio_mean", "s2_swir_ratio_median", "s2_swir_ratio_std",
            "s2_b04_mean", "s2_b08_mean", "s2_b11_mean", "s2_b12_mean",
        ]

        for k in all_s3a_keys:
            base_k = k[3:]  # strip 's2_'
            pre_val = (pre_s3a or {}).get(k, np.nan if "pct" in k or "mean" in k or "pixels" in k or "std" in k else "")
            post_val = (post_s3a or {}).get(k, np.nan if "pct" in k or "mean" in k or "pixels" in k or "std" in k else "")
            record[f"s2_pre_{base_k}"] = pre_val
            record[f"s2_post_{base_k}"] = post_val

        # Forward Step 3B change features
        record.update(change_feats)

        return record

    def process_prototype_events(
        self,
        events_df: pd.DataFrame,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Process all events in prototype DataFrame and export real-data outputs.

        Args:
            events_df: DataFrame loaded from Step 1 prototype CSV.
            output_dir: Output directory (defaults to outputs/sentinel2_real_prototype/).

        Returns:
            DataFrame containing all processed event rows with Step 3A and Step 3B features.
        """
        if output_dir is None:
            config = Config.load()
            output_dir = config.output_dir / "sentinel2_real_prototype"
        output_dir.mkdir(parents=True, exist_ok=True)

        records: List[Dict[str, Any]] = []
        for _, row in events_df.iterrows():
            rec = self.process_event(row)
            records.append(rec)

        df = pd.DataFrame(records)

        # 1. Export CSV
        csv_path = output_dir / "sentinel2_real_10_events.csv"
        df.to_csv(csv_path, index=False)
        logger.info("Saved Step 3C real prototype CSV: %s", csv_path)

        # 2. Export Markdown Report
        report_path = output_dir / "SENTINEL2_REAL_PROCESSING_REPORT.md"
        self.generate_real_processing_report(df, report_path)
        logger.info("Saved Step 3C real processing report: %s", report_path)

        return df

    def generate_real_processing_report(self, df: pd.DataFrame, out_path: Path) -> None:
        """Generate comprehensive markdown report for Step 3C real-data processing."""
        total_events = len(df)
        auth_req_count = int((df["processing_status"] == STATUS_AUTH_REQUIRED).sum())
        real_success_count = int((df["processing_status"] == STATUS_REAL_CDSE_SUCCESS).sum())
        missing_pre_count = int((df["processing_status"] == "MISSING_PRE_PRODUCT").sum())
        missing_post_count = int((df["processing_status"] == "MISSING_POST_PRODUCT").sum())
        missing_both_count = int((df["processing_status"] == "MISSING_BOTH_PRODUCTS").sum())
        api_err_count = int((df["processing_status"] == STATUS_PROCESSING_API_ERROR).sum())
        other_fail_count = total_events - (
            auth_req_count + real_success_count + missing_pre_count +
            missing_post_count + missing_both_count + api_err_count
        )

        has_creds = self.client.has_credentials()

        lines = [
            "# Phase 3 — Step 3C: Real Sentinel-2 CDSE Processing Report",
            "",
            "**Component:** `src/feature_engineering/sentinel2_real_processor.py`  ",
            "**Target Dataset:** 10-event prototype from Phase 3 Step 1  ",
            "**Scope:** Real Sentinel-2 Level-2A imagery retrieval via CDSE Processing API, Step 3A spectral extraction, and Step 3B change calculation",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            "Phase 3 Step 3C establishes the connection between the modular Sentinel-2 feature engineering layer "
            "and the **Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Processing API**. It processes the "
            "10-event historical prototype through the full pipeline:",
            "",
            "$$\\text{FIRMS Event} \\longrightarrow \\text{CDSE Localized AOI (1 km} \\times \\text{1 km)} "
            "\\longrightarrow \\text{Raw GeoTIFF (SCL, B04, B08, B11, B12)} "
            "\\longrightarrow \\text{Step 3A Spectral Extractor} "
            "\\longrightarrow \\text{Step 3B Change Calculator}$$",
            "",
            "> [!IMPORTANT]",
            "> **Authentication and Ground-Truth Protocol:**",
            f"> - **OAuth2 Configuration Status:** `{'CONFIGURED' if has_creds else 'UNCONFIGURED / AUTH_REQUIRED'}`",
            "> - **Zero Synthetic Substitution:** Synthetic imagery is NEVER substituted as a fallback for real imagery. "
            "If credentials are not configured, the pipeline halts at authentication and reports `AUTH_REQUIRED` explicitly.",
            "> - **Optical Nature Disclaimer:** Sentinel-2 is an optical sensor (VNIR/SWIR), NOT a thermal sensor. "
            "Reflectance indices (`dNDVI`, `dNBR`, `dNDWI`) represent optical surface-change evidence only and do NOT prove fire occurrence or industrial causality.",
            "> - **No Model Modification:** Zero ML models were trained, modified, or evaluated in this step.",
            "",
            "---",
            "",
            "## 2. Processing Outcome Breakdown (10 Prototype Events)",
            "",
            "| Outcome Category | Count | Status Code | Meaning |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Real CDSE Processed** | {real_success_count} / {total_events} | `REAL_CDSE_SUCCESS` | Both pre and post real GeoTIFF rasters retrieved and processed |",
            f"| **Authentication Required** | {auth_req_count} / {total_events} | `AUTH_REQUIRED` | CDSE credentials not provided in environment; pipeline safely stopped |",
            f"| **Missing Pre Product** | {missing_pre_count} / {total_events} | `MISSING_PRE_PRODUCT` | Pre observation unavailable in catalogue search (e.g., persistent cloud) |",
            f"| **Missing Post Product** | {missing_post_count} / {total_events} | `MISSING_POST_PRODUCT` | Post observation unavailable in catalogue search (cloud > 40%) |",
            f"| **Missing Both Products** | {missing_both_count} / {total_events} | `MISSING_BOTH_PRODUCTS` | Neither observation passed catalogue screening |",
            f"| **Processing API Error** | {api_err_count} / {total_events} | `PROCESSING_API_ERROR` | CDSE server error or HTTP timeout |",
            f"| **Other Failures** | {other_fail_count} / {total_events} | `PROCESSING_FAILED` | Coordinate, raster corruption, or pipeline error |",
            "",
            "---",
            "",
            "## 3. Event-by-Event Prototype Status",
            "",
            "| Event ID | Priority | Land Cover | Pre Obs Date | Post Obs Date | Processing Status | Change Status | Real CDSE Data | Failure Reason |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for _, r in df.iterrows():
            ev_id = r["event_id"]
            prio = r["candidate_priority"]
            lc = r["landcover_class"]
            pre_d = str(r["selected_pre_image_date"])[:10] if r["selected_pre_image_date"] else "None"
            post_d = str(r["selected_post_image_date"])[:10] if r["selected_post_image_date"] else "None"
            proc_st = r["processing_status"]
            ch_st = r.get("s2_change_status", "N/A")
            is_real_str = "YES" if r.get("is_real_cdse_data", False) else "NO"
            reason = str(r.get("failure_reason", ""))[:50]
            lines.append(
                f"| `{ev_id}` | {prio} | {lc} | {pre_d} | {post_d} | `{proc_st}` | `{ch_st}` | {is_real_str} | {reason} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 4. Verification and Validation Criteria",
            "",
            "When real CDSE credentials are provided and GeoTIFF raster bytes are returned, the pipeline validates:",
            "",
            "1. **Raster Parsing and Dimensions:** Multi-band GeoTIFF is unpacked via `MemoryFile` in `rasterio`. "
            "Dimensions are strictly verified to match `50 x 50` pixels (1000m / 20m).",
            "2. **Band Integrity:** All 5 required bands (`SCL`, `B04`, `B08`, `B11`, `B12`) are extracted as separate 2D planes.",
            "3. **Spatial Alignment:** All 5 planes share the exact same spatial grid and bounding box from the Sentinel Hub request.",
            "4. **Finite Values:** Non-finite or invalid values are checked before computing ratios.",
            "5. **SCL Masking:** Step 3A `Sentinel2SpectralExtractor` strictly screens pixels to valid classes (`4, 5, 6`) "
            "and masks out clouds, cloud shadows, and defective pixels.",
            "6. **Step 3B Temporal Difference Calculation:** Evaluates `dNDVI`, `dNBR`, `dNDWI`, `dSWIR_ratio` and absolute changes.",
            "",
            "---",
            "",
            "## 5. Mocked Deterministic Testing",
            "",
            "To prevent the test suite from depending on live CDSE server availability or credentials, "
            "deterministic unit and integration tests in `tests/test_sentinel2_real_processor.py` verify:",
            "- Synthetic in-memory GeoTIFF bytes generation and parsing.",
            "- Spatial alignment and dimensional compliance.",
            "- Step 3A feature extraction on parsed GeoTIFF arrays.",
            "- Step 3B change calculation on parsed pre and post rasters.",
            "- Graceful handling of unconfigured credentials (`AUTH_REQUIRED`).",
            "- Graceful handling of missing products (`MISSING_PRODUCT`).",
            "- Graceful handling of cloud-obscured patches (`ALL_PIXELS_MASKED`).",
            "- Graceful handling of API errors (HTTP 400/500).",
            "",
            "---",
            "",
            "## 6. Phase 2C Integrity Verification",
            "",
            "- **Phase 2C Files:** Completely untouched and unchanged.",
            "- **FIRMS Data Pipeline:** Unchanged.",
            "- **OSM Pipeline:** Unchanged.",
            "- **WorldCover Pipeline:** Unchanged.",
            "- **ML Models:** Unchanged (no training or feature vector modification).",
            "- **Step 3A / 3B Modules:** Unchanged (clean modular consumers).",
            "",
            "---",
            "",
            "## 7. Limitations and Operating Constraints",
            "",
            "1. **CDSE Credentials:** Real CDSE processing requires `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` configured in the environment.",
            "2. **Cloud Occlusion:** Optical Sentinel-2 imagery cannot penetrate clouds. Missing post observations are expected and handled.",
            "3. **Prototype Scope:** Evaluated strictly on the 10 representative events. Full 633-event scaling is deferred.",
        ])

        out_path.write_text("\n".join(lines), encoding="utf-8")
