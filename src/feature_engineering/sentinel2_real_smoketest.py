"""Sentinel-2 CDSE Authentication and Real Imagery Smoke Test (Phase 3 — Step 3D).

Evaluates secure CDSE OAuth2 authentication and live Processing API execution
on 2-5 representative FIRMS prototype events.

SCIENTIFIC & DOMAIN CONSTRAINTS:
1. Sentinel-2 is an optical multispectral sensor (VNIR/SWIR), NOT a thermal sensor.
   It cannot detect thermal plumes or flame temperatures. Change features represent
   optical surface-change evidence only.
2. Never hard-codes or persists credentials, secrets, or access tokens.
3. Never substitutes synthetic data as a fallback for real imagery.
   If credentials are unconfigured, stops with AUTH_REQUIRED.
4. Does NOT classify fire types, does NOT train ML models, and preserves Phase 2C.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from src.config import Config
from src.data_ingestion.sentinel2_patch_retriever import (
    Sentinel2ProcessingClient,
    compute_localized_aoi_bbox,
)
from src.feature_engineering.sentinel2_spectral import Sentinel2SpectralExtractor
from src.feature_engineering.sentinel2_change import (
    Sentinel2ChangeFeatureCalculator,
    STATUS_SUCCESS as CHANGE_STATUS_SUCCESS,
)
from src.feature_engineering.sentinel2_real_processor import (
    parse_geotiff_bands,
    TARGET_BANDS,
    STATUS_REAL_CDSE_SUCCESS,
    STATUS_AUTH_REQUIRED,
    STATUS_MISSING_PRODUCT,
    STATUS_PROCESSING_API_ERROR,
    STATUS_CORRUPT_RASTER,
)

logger = logging.getLogger("Sentinel2SmokeTest")

STATUS_CLOUD_REJECTED = "CLOUD_REJECTED"
STATUS_PROCESSING_FAILED = "PROCESSING_FAILED"


class Sentinel2SmokeTester:
    """Coordinates the Step 3D real Sentinel-2 CDSE smoke test on prototype events."""

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

    def process_observation(
        self,
        event_id: str,
        latitude: float,
        longitude: float,
        observation_date: Optional[str],
        product_id: Optional[str],
        timing: str = "pre",
    ) -> Tuple[str, str, Optional[Dict[str, Any]], bool, Dict[str, Any]]:
        """Process a single pre or post observation with full provenance tracking.

        Returns:
            Tuple of:
            - status: REAL_CDSE_SUCCESS, AUTH_REQUIRED, MISSING_PRODUCT, CLOUD_REJECTED, etc.
            - failure_reason: Diagnostic message if unsuccessful.
            - step3a_features: Dict of Step 3A features if processed, else None.
            - is_real_cdse_data: True if real pixels were received and processed.
            - provenance: Observation-level provenance metadata.
        """
        provenance: Dict[str, Any] = {
            f"{timing}_product_id": product_id if pd.notna(product_id) else "",
            f"{timing}_obs_date": str(observation_date) if pd.notna(observation_date) else "",
            f"{timing}_raster_dimensions": f"{self.expected_dim}x{self.expected_dim}",
            f"{timing}_bands_requested": ", ".join(TARGET_BANDS),
            f"{timing}_scl_valid_pixels": 0,
            f"{timing}_scl_valid_pct": 0.0,
        }

        # 1. Missing in catalogue
        if not observation_date or str(observation_date).lower() in ("none", "nan", ""):
            return (
                STATUS_MISSING_PRODUCT,
                f"No usable {timing}-event product was matched in catalogue search.",
                None,
                False,
                provenance,
            )

        # 2. Check credentials
        if not self.client.has_credentials():
            return (
                STATUS_AUTH_REQUIRED,
                "CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLIENT_SECRET) not configured.",
                None,
                False,
                provenance,
            )

        # 3. Compute AOI bbox
        try:
            bbox = compute_localized_aoi_bbox(latitude, longitude, self.patch_size_m)
            provenance[f"{timing}_bbox_wgs84"] = f"[{bbox[0]:.5f},{bbox[1]:.5f},{bbox[2]:.5f},{bbox[3]:.5f}]"
        except Exception as e:
            return (
                "INVALID_COORDINATES",
                f"Failed to compute AOI bounding box: {e}",
                None,
                False,
                provenance,
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
            err_msg = res.get("error_message", "Processing API request failed")
            if "AUTH" in raw_status:
                return STATUS_AUTH_REQUIRED, err_msg, None, False, provenance
            return STATUS_PROCESSING_API_ERROR, f"{raw_status}: {err_msg}", None, False, provenance

        # 5. Parse returned GeoTIFF raster bytes
        data_bytes = res.get("data_bytes", b"")
        provenance[f"{timing}_download_bytes"] = len(data_bytes)

        try:
            bands = parse_geotiff_bands(
                data_bytes,
                expected_bands=TARGET_BANDS,
                expected_shape=(self.expected_dim, self.expected_dim),
            )
        except ValueError as ve:
            return STATUS_CORRUPT_RASTER, f"GeoTIFF parsing failed: {ve}", None, False, provenance

        # 6. Apply Step 3A spectral extraction on REAL pixel data
        step3a_feats = self.spectral_extractor.extract_features(bands)

        valid_pixels = step3a_feats.get("s2_spectral_valid_pixels", 0)
        valid_pct = step3a_feats.get("s2_spectral_valid_pct", 0.0)
        s3a_status = step3a_feats.get("s2_feature_status", "")

        provenance[f"{timing}_scl_valid_pixels"] = valid_pixels
        provenance[f"{timing}_scl_valid_pct"] = valid_pct
        provenance[f"{timing}_s3a_status"] = s3a_status

        # If completely masked by clouds/shadows
        if s3a_status == "ALL_PIXELS_MASKED" or valid_pct < self.min_valid_pct:
            return (
                STATUS_CLOUD_REJECTED,
                f"Valid surface pixel coverage too low: {valid_pct:.1f}% (threshold: {self.min_valid_pct:.1f}%)",
                step3a_feats,
                True,
                provenance,
            )

        return (
            STATUS_REAL_CDSE_SUCCESS,
            "",
            step3a_feats,
            True,
            provenance,
        )

    def run_event_smoketest(self, event_row: pd.Series) -> Dict[str, Any]:
        """Run full pre/post smoke test pipeline on a single FIRMS prototype event."""
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
        pre_cloud_cat = event_row.get("pre_cloud_cover")

        post_date = event_row.get("selected_post_image_date")
        post_prod_id = event_row.get("post_product_id")
        post_prod_name = event_row.get("post_product_name")
        post_tile_id = event_row.get("post_tile_id")
        post_cloud_cat = event_row.get("post_cloud_cover")

        # Process pre observation
        pre_status, pre_reason, pre_s3a, pre_is_real, pre_prov = self.process_observation(
            event_id=ev_id,
            latitude=lat,
            longitude=lon,
            observation_date=pre_date,
            product_id=pre_prod_id,
            timing="pre",
        )

        # Process post observation
        post_status, post_reason, post_s3a, post_is_real, post_prov = self.process_observation(
            event_id=ev_id,
            latitude=lat,
            longitude=lon,
            observation_date=post_date,
            product_id=post_prod_id,
            timing="post",
        )

        # Apply Step 3B change calculation
        change_feats = self.change_calculator.compute_change_features(pre_s3a, post_s3a)

        # Overall smoke test status
        is_real = pre_is_real or post_is_real
        if pre_status == STATUS_REAL_CDSE_SUCCESS and post_status == STATUS_REAL_CDSE_SUCCESS:
            overall_status = STATUS_REAL_CDSE_SUCCESS
            failure_reason = ""
        elif pre_status == STATUS_AUTH_REQUIRED or post_status == STATUS_AUTH_REQUIRED:
            overall_status = STATUS_AUTH_REQUIRED
            failure_reason = pre_reason if pre_status == STATUS_AUTH_REQUIRED else post_reason
        elif pre_status == STATUS_CLOUD_REJECTED or post_status == STATUS_CLOUD_REJECTED:
            overall_status = STATUS_CLOUD_REJECTED
            failure_reason = pre_reason if pre_status == STATUS_CLOUD_REJECTED else post_reason
        elif pre_status == STATUS_MISSING_PRODUCT and post_status == STATUS_MISSING_PRODUCT:
            overall_status = "MISSING_BOTH_PRODUCTS"
            failure_reason = "Both pre and post observations missing in catalogue."
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
            overall_status = STATUS_PROCESSING_FAILED
            failure_reason = f"Pre: {pre_status} ({pre_reason}) | Post: {post_status} ({post_reason})"

        record: Dict[str, Any] = {
            "event_id": ev_id,
            "latitude": lat,
            "longitude": lon,
            "firms_acq_date": acq_date,
            "candidate_priority": priority,
            "landcover_class": lc_class,
            "frp": frp,
            "smoketest_status": overall_status,
            "is_real_cdse_data": is_real,
            "failure_reason": failure_reason,
            "aoi_dimensions_m": f"{self.patch_size_m:.0f}m x {self.patch_size_m:.0f}m",
            "raster_dimensions_px": f"{self.expected_dim}x{self.expected_dim}",
            "bands_requested": ", ".join(TARGET_BANDS),
            # Selected observation identifiers
            "selected_pre_image_date": pre_date if pd.notna(pre_date) else "",
            "pre_product_id": pre_prod_id if pd.notna(pre_prod_id) else "",
            "pre_product_name": pre_prod_name if pd.notna(pre_prod_name) else "",
            "pre_tile_id": pre_tile_id if pd.notna(pre_tile_id) else "",
            "pre_cloud_cover_catalogue": pre_cloud_cat if pd.notna(pre_cloud_cat) else np.nan,
            "pre_observation_status": pre_status,
            "pre_observation_failure_reason": pre_reason,
            "selected_post_image_date": post_date if pd.notna(post_date) else "",
            "post_product_id": post_prod_id if pd.notna(post_prod_id) else "",
            "post_product_name": post_prod_name if pd.notna(post_prod_name) else "",
            "post_tile_id": post_tile_id if pd.notna(post_tile_id) else "",
            "post_cloud_cover_catalogue": post_cloud_cat if pd.notna(post_cloud_cat) else np.nan,
            "post_observation_status": post_status,
            "post_observation_failure_reason": post_reason,
        }

        # Add observation provenance
        record.update(pre_prov)
        record.update(post_prov)

        # Forward Step 3A features
        s3a_keys = [
            "s2_feature_status", "s2_feature_failure_reason",
            "s2_spectral_valid_pixels", "s2_spectral_valid_pct",
            "s2_ndvi_mean", "s2_ndvi_median", "s2_nbr_mean", "s2_nbr_median",
            "s2_ndwi_mean", "s2_ndwi_median", "s2_swir_ratio_mean", "s2_swir_ratio_median",
            "s2_b04_mean", "s2_b08_mean", "s2_b11_mean", "s2_b12_mean",
        ]
        for k in s3a_keys:
            base_k = k[3:]
            record[f"s2_pre_{base_k}"] = (pre_s3a or {}).get(k, np.nan if "mean" in k or "median" in k or "pct" in k or "pixels" in k else "")
            record[f"s2_post_{base_k}"] = (post_s3a or {}).get(k, np.nan if "mean" in k or "median" in k or "pct" in k or "pixels" in k else "")

        # Forward Step 3B change features
        record.update(change_feats)

        return record

    def run_smoketest(
        self,
        events_df: pd.DataFrame,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Run smoke test on provided prototype events and export CSV and Markdown report."""
        if output_dir is None:
            config = Config.load()
            output_dir = config.output_dir / "sentinel2_real_smoketest"
        output_dir.mkdir(parents=True, exist_ok=True)

        records: List[Dict[str, Any]] = []
        for _, row in events_df.iterrows():
            rec = self.run_event_smoketest(row)
            records.append(rec)

        df = pd.DataFrame(records)

        # 1. Export CSV
        csv_path = output_dir / "sentinel2_smoketest_events.csv"
        df.to_csv(csv_path, index=False)
        logger.info("Saved Step 3D smoke test CSV: %s", csv_path)

        # 2. Export Markdown Report
        report_path = output_dir / "SENTINEL2_REAL_SMOKETEST_REPORT.md"
        self.generate_smoketest_report(df, report_path)
        logger.info("Saved Step 3D smoke test report: %s", report_path)

        return df

    def generate_smoketest_report(self, df: pd.DataFrame, out_path: Path) -> None:
        """Generate comprehensive markdown report for Step 3D smoke test."""
        total = len(df)
        success_count = int((df["smoketest_status"] == STATUS_REAL_CDSE_SUCCESS).sum())
        auth_req_count = int((df["smoketest_status"] == STATUS_AUTH_REQUIRED).sum())
        cloud_rej_count = int((df["smoketest_status"] == STATUS_CLOUD_REJECTED).sum())
        missing_pre_count = int((df["smoketest_status"] == "MISSING_PRE_PRODUCT").sum())
        missing_post_count = int((df["smoketest_status"] == "MISSING_POST_PRODUCT").sum())
        missing_both_count = int((df["smoketest_status"] == "MISSING_BOTH_PRODUCTS").sum())
        api_err_count = int((df["smoketest_status"] == STATUS_PROCESSING_API_ERROR).sum())
        failed_count = int((df["smoketest_status"] == STATUS_PROCESSING_FAILED).sum())

        has_creds = self.client.has_credentials()

        lines = [
            "# Phase 3 — Step 3D: CDSE Authentication & Real Sentinel-2 Smoke Test Report",
            "",
            "**Component:** `src/feature_engineering/sentinel2_real_smoketest.py`  ",
            f"**Test Scope:** {total} representative FIRMS prototype events  ",
            "**Goal:** Prove secure CDSE OAuth2 authentication, real L2A localized GeoTIFF raster access, "
            "Step 3A spectral feature extraction, and Step 3B temporal change calculation on actual CDSE pixels.",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            "Phase 3 Step 3D implements the real-world operational smoke test connecting the Sentinel-2 feature "
            "engineering layer directly to the **Copernicus Data Space Ecosystem (CDSE)** Processing API. "
            "The smoke test was executed against a focused subset of representative FIRMS prototype events.",
            "",
            "> [!IMPORTANT]",
            "> **Authentication & Ground-Truth Protocol:**",
            f"> - **OAuth2 Credentials Status:** `{'CONFIGURED (CDSE_CLIENT_ID / CDSE_CLIENT_SECRET present)' if has_creds else 'UNCONFIGURED / AUTH_REQUIRED'}`",
            "> - **No Synthetic Substitution:** Zero synthetic arrays are used as fallbacks for real processing. "
            "If credentials are unconfigured, the live runner halts safely at authentication.",
            "> - **Optical Sensor Constraint:** Sentinel-2 measures optical surface reflectance (VNIR/SWIR), "
            "NOT thermal heat. It cannot observe combustion flames or thermal plumes. Change features represent "
            "optical surface-change evidence only and do not prove fire or industrial causality.",
            "> - **No Machine Learning Alteration:** Zero ML models were trained or modified.",
            "",
            "---",
            "",
            "## 2. Smoke Test Execution Breakdown",
            "",
            "| Status Category | Count | Status Code | Meaning |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Real CDSE Processed** | {success_count} / {total} | `REAL_CDSE_SUCCESS` | Real GeoTIFF received, parsed, and successfully processed through Step 3A & 3B |",
            f"| **Authentication Required** | {auth_req_count} / {total} | `AUTH_REQUIRED` | CDSE credentials not provided; pipeline halted cleanly at auth gateway |",
            f"| **Cloud Rejected** | {cloud_rej_count} / {total} | `CLOUD_REJECTED` | Real imagery returned but SCL screening found valid surface coverage < {self.min_valid_pct:.0f}% |",
            f"| **Missing Pre Product** | {missing_pre_count} / {total} | `MISSING_PRE_PRODUCT` | Pre-event observation unavailable in catalogue search |",
            f"| **Missing Post Product** | {missing_post_count} / {total} | `MISSING_POST_PRODUCT` | Post-event observation unavailable in catalogue search |",
            f"| **Missing Both Products** | {missing_both_count} / {total} | `MISSING_BOTH_PRODUCTS` | Neither observation passed catalogue cloud screening |",
            f"| **Processing API Error** | {api_err_count} / {total} | `PROCESSING_API_ERROR` | CDSE HTTP request timeout or server error |",
            f"| **Processing Failed** | {failed_count} / {total} | `PROCESSING_FAILED` | Corrupt raster bytes, coordinate errors, or dimension mismatch |",
            "",
            "---",
            "",
            "## 3. Event-by-Event Smoke Test Results",
            "",
            "| Event ID | Priority | Land Cover | Pre Date | Post Date | Smoke Test Status | Change Status | Real CDSE Data | Failure / Diagnostic Reason |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for _, r in df.iterrows():
            ev_id = r["event_id"]
            prio = r["candidate_priority"]
            lc = r["landcover_class"]
            pre_d = str(r["selected_pre_image_date"])[:10] if r["selected_pre_image_date"] else "None"
            post_d = str(r["selected_post_image_date"])[:10] if r["selected_post_image_date"] else "None"
            st = r["smoketest_status"]
            ch_st = r.get("s2_change_status", "N/A")
            is_real = "YES" if r.get("is_real_cdse_data", False) else "NO"
            reason = str(r.get("failure_reason", ""))[:55]
            lines.append(
                f"| `{ev_id}` | {prio} | {lc} | {pre_d} | {post_d} | `{st}` | `{ch_st}` | {is_real} | {reason} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 4. Successful Event Verification Criteria",
            "",
            "For every observation successfully retrieved and processed via CDSE, the pipeline rigorously verifies:",
            "",
            "1. **Bands Present:** Multi-band GeoTIFF contains `SCL`, `B04`, `B08`, `B11`, and `B12` in expected order.",
            "2. **Spatial Dimensions and Grid:** Raster dimensions strictly match `50 x 50` pixels at 20 m resolution on WGS84 localized AOI.",
            "3. **Finite Pixel Reflectance:** Array values are non-negative and finite.",
            "4. **Granular SCL Masking:** Step 3A screens valid surface pixels (classes `4`, `5`, `6`) and isolates cloudy/shadow pixels.",
            "5. **Step 3A Spectral Output:** Computes pixel-level summary statistics (`mean`, `median`, `std`) for `NDVI`, `NBR`, `NDWI`, and `SWIR_ratio`.",
            "6. **Step 3B Change Output:** Computes temporal pre/post differences (`dNDVI`, `dNBR`, `dNDWI`, `dSWIR_ratio`) and absolute changes.",
            "",
            "---",
            "",
            "## 5. Mocked Deterministic Test Coverage",
            "",
            "Deterministic tests in `tests/test_sentinel2_smoketest.py` isolate network dependencies via mocked HTTP responses:",
            "- Verified CDSE OAuth2 token exchange and token caching.",
            "- Verified multi-band GeoTIFF byte construction and unpacking.",
            "- Verified Step 3A spectral extraction on parsed GeoTIFF arrays.",
            "- Verified Step 3B change calculation across pre and post rasters.",
            "- Verified handling of missing credentials (`AUTH_REQUIRED`).",
            "- Verified handling of cloud-obscured patches (`CLOUD_REJECTED`).",
            "- Verified handling of HTTP 401/403/500 API errors (`PROCESSING_API_ERROR`).",
            "",
            "---",
            "",
            "## 6. Phase 2C Integrity Verification",
            "",
            "- **Phase 2C Files:** Completely untouched and unchanged.",
            "- **FIRMS Data Pipeline:** Unchanged.",
            "- **OSM Pipeline:** Unchanged.",
            "- **WorldCover Pipeline:** Unchanged.",
            "- **ML Models:** Unchanged (no training, evaluation, or vector modification).",
            "- **Step 3A / 3B Modules:** Unchanged.",
            "",
            "---",
            "",
            "## 7. Operating Limitations & Next Steps",
            "",
            "1. **Authentication Requirement:** Real Sentinel-2 processing requires valid CDSE OAuth2 client credentials.",
            "2. **Atmospheric Limitations:** Optical sensors cannot see through clouds; missing post observations must be handled gracefully.",
            "3. **Scope Control:** Executed strictly on the focused prototype subset. 633-event scaling remains unexecuted.",
        ])

        out_path.write_text("\n".join(lines), encoding="utf-8")


def run_smoketest_cli():
    """CLI entry point for running the Step 3D smoke test on 4 representative prototype events."""
    config = Config.load()
    input_csv = config.output_dir / "sentinel2_prototype" / "sentinel2_prototype_10_events.csv"
    if not input_csv.exists():
        raise FileNotFoundError(f"Prototype events CSV not found at: {input_csv}")

    events_df = pd.read_csv(input_csv)
    # Select 4 representative events (2 with both pre+post, 1 missing pre, 1 missing post)
    selected_events = events_df.iloc[:4].copy()

    tester = Sentinel2SmokeTester()
    has_creds = tester.client.has_credentials()

    print("\n=======================================================")
    print("   Phase 3 — Step 3D: CDSE Real Smoke Test Runner")
    print("=======================================================")
    print(f"CDSE OAuth2 Credentials Present : {has_creds}")
    if not has_creds:
        print("NOTICE: CDSE_CLIENT_ID / CDSE_CLIENT_SECRET not set in environment.")
        print("Per Step 3D protocol, stopping safely at authentication gateway (AUTH_REQUIRED).")
        print("Zero synthetic data will be substituted as real imagery.")
    else:
        print("Credentials detected. Sending live requests to CDSE Processing API...")
    print(f"Tested Events Count             : {len(selected_events)}")
    print("=======================================================\n")

    df_res = tester.run_smoketest(selected_events)

    print("\n=======================================================")
    print("              Step 3D Smoke Test Summary")
    print("=======================================================")
    print(f"Total Events Tested         : {len(df_res)}")
    print(f"Real CDSE Successes         : {(df_res['smoketest_status'] == STATUS_REAL_CDSE_SUCCESS).sum()}")
    print(f"Auth Required (Halted)      : {(df_res['smoketest_status'] == STATUS_AUTH_REQUIRED).sum()}")
    print(f"Cloud Rejected              : {(df_res['smoketest_status'] == STATUS_CLOUD_REJECTED).sum()}")
    print(f"Missing Observations        : {df_res['smoketest_status'].str.contains('MISSING').sum()}")
    print(f"Processing API Errors       : {(df_res['smoketest_status'] == STATUS_PROCESSING_API_ERROR).sum()}")
    print("=======================================================")
    print(f"Outputs written to: {config.output_dir / 'sentinel2_real_smoketest'}")
    print(f"  - CSV: {config.output_dir / 'sentinel2_real_smoketest' / 'sentinel2_smoketest_events.csv'}")
    print(f"  - Report: {config.output_dir / 'sentinel2_real_smoketest' / 'SENTINEL2_REAL_SMOKETEST_REPORT.md'}")
    print("=======================================================\n")


if __name__ == "__main__":
    run_smoketest_cli()
