"""Prototype execution script for Phase 3 Step 3C: Real Sentinel-2 CDSE Processing.

Runs the complete pre/post Sentinel-2 Level-2A pipeline on the 10-event prototype:
1. Localized 1 km x 1 km AOI retrieval via CDSE Processing API
2. Real multi-band GeoTIFF parsing (SCL, B04, B08, B11, B12)
3. Step 3A spectral feature extraction (NDVI, NBR, NDWI, SWIR ratio)
4. Step 3B temporal change feature calculation (dNDVI, dNBR, dNDWI, etc.)
5. Quality assurance and status tracking (AUTH_REQUIRED / REAL_CDSE_SUCCESS / MISSING_PRODUCT)

Exports:
1. outputs/sentinel2_real_prototype/sentinel2_real_10_events.csv
2. outputs/sentinel2_real_prototype/SENTINEL2_REAL_PROCESSING_REPORT.md

SCIENTIFIC CONSTRAINTS:
- Sentinel-2 is optical (VNIR/SWIR), NOT thermal. It cannot observe flames or heat.
- Change features represent optical surface-change evidence only.
- Does NOT classify fire, does NOT train ML models, and does NOT modify Phase 2C.
- Never substitutes synthetic data for real imagery when credentials are unconfigured.
"""

import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.config import Config
from src.feature_engineering.sentinel2_real_processor import (
    Sentinel2RealProcessor,
    STATUS_AUTH_REQUIRED,
    STATUS_REAL_CDSE_SUCCESS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Sentinel2RealPrototype")


def run_real_prototype():
    """Execute Step 3C real CDSE processing pipeline on the 10-event prototype."""
    config = Config.load()
    input_csv = config.output_dir / "sentinel2_prototype" / "sentinel2_prototype_10_events.csv"
    if not input_csv.exists():
        raise FileNotFoundError(
            f"Step 1 prototype CSV not found at: {input_csv}. "
            "Please run Phase 3 Step 1 first."
        )

    events_df = pd.read_csv(input_csv)
    output_dir = config.output_dir / "sentinel2_real_prototype"
    output_dir.mkdir(parents=True, exist_ok=True)

    processor = Sentinel2RealProcessor()

    has_creds = processor.client.has_credentials()
    logger.info("=== Phase 3 — Step 3C: Real Sentinel-2 CDSE Processing ===")
    logger.info("CDSE OAuth2 credentials configured: %s", has_creds)
    if not has_creds:
        logger.warning(
            "CDSE credentials not found in environment (CDSE_CLIENT_ID / CDSE_CLIENT_SECRET). "
            "Per Step 3C specification, pipeline will stop at authentication and record AUTH_REQUIRED. "
            "Zero synthetic data will be substituted as real imagery."
        )
    else:
        logger.info("Credentials found. Attempting real CDSE Processing API requests.")

    df_results = processor.process_prototype_events(events_df, output_dir=output_dir)

    # Print summary
    total = len(df_results)
    auth_req = int((df_results["processing_status"] == STATUS_AUTH_REQUIRED).sum())
    real_success = int((df_results["processing_status"] == STATUS_REAL_CDSE_SUCCESS).sum())
    missing_pre = int((df_results["processing_status"] == "MISSING_PRE_PRODUCT").sum())
    missing_post = int((df_results["processing_status"] == "MISSING_POST_PRODUCT").sum())

    print("\n=======================================================")
    print("      Step 3C: Real CDSE Processing Summary")
    print("=======================================================")
    print(f"Total Prototype Events Processed : {total}")
    print(f"Real CDSE Rasters Successfully Processed: {real_success}")
    print(f"Authentication Required (Halted) : {auth_req}")
    print(f"Missing Pre Observation (Catalogue) : {missing_pre}")
    print(f"Missing Post Observation (Catalogue) : {missing_post}")
    print("=======================================================")
    print(f"Outputs written to: {output_dir}")
    print(f"  - CSV: {output_dir / 'sentinel2_real_10_events.csv'}")
    print(f"  - Report: {output_dir / 'SENTINEL2_REAL_PROCESSING_REPORT.md'}")
    print("=======================================================\n")

    return df_results


if __name__ == "__main__":
    run_real_prototype()
