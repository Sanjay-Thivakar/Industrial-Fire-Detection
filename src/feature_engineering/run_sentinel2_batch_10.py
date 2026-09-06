"""Execution script for Phase 3E Controlled 10-Event Real Sentinel-2 Batch.

Processes exactly 10 representative FIRMS events from validation_candidates_v2.csv
using Sentinel2ScaleProcessor with real CDSE Sentinel-2 Level-2A data.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from src.config import Config
from src.data_ingestion.run_sentinel2_prototype import select_10_representative_events
from src.feature_engineering.sentinel2_scale_processor import (
    Sentinel2ScaleProcessor,
    STATUS_REAL_CDSE_SUCCESS,
    STATUS_PARTIAL_PRE_ONLY,
    STATUS_PARTIAL_POST_ONLY,
    STATUS_CLOUD_REJECTED,
    STATUS_MISSING_PRODUCT,
    STATUS_AUTH_REQUIRED,
    STATUS_PROCESSING_API_ERROR,
    STATUS_CORRUPT_RASTER,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Sentinel2Batch10")


def generate_batch_report(
    df: pd.DataFrame,
    out_path: Path,
    metrics: Dict[str, Any],
) -> None:
    """Write markdown validation report for the 10-event batch."""
    lines = [
        "# Sentinel-2 Real-Processing Validation Batch Report (10 Events)",
        "",
        "## Executive Summary",
        "",
        f"- **Total Events Attempted:** `{metrics['total_events']}`",
        f"- **Real CDSE Successes (Full Pre & Post):** `{metrics['real_success_full']}`",
        f"- **Partial Success (Pre-only):** `{metrics['partial_pre']}`",
        f"- **Partial Success (Post-only):** `{metrics['partial_post']}`",
        f"- **Total Events with Real CDSE Data:** `{metrics['real_cdse_any']}`",
        f"- **Real Sentinel-2 Coverage Rate:** `{metrics['coverage_pct']:.1f}%`",
        f"- **Missing Pre-event Observations:** `{metrics['missing_pre']}`",
        f"- **Missing Post-event Observations:** `{metrics['missing_post']}`",
        f"- **Missing Both Pre & Post:** `{metrics['missing_both']}`",
        f"- **Insufficient Valid Data (Cloud/Shadow Rejected):** `{metrics['insufficient_valid_events']}` (Pre: {metrics['insufficient_pre']}, Post: {metrics['insufficient_post']})",
        f"- **Authentication / API Failures:** `{metrics['auth_failures'] + metrics['api_failures']}` (Auth: {metrics['auth_failures']}, API: {metrics['api_failures']})",
        f"- **Other Failures:** `{metrics['other_failures']}`",
        f"- **Successfully Calculated Single-Observation Feature Sets:** `{metrics['successful_feature_records']}`",
        f"- **Successfully Calculated Temporal Change Sets (Step 3B):** `{metrics['events_with_change_feats']}`",
        f"- **Sentinel-2 Observation Date Range:** `{metrics['obs_date_range']}`",
        f"- **Total Batch Runtime:** `{metrics['total_runtime_s']:.2f} seconds`",
        "",
        "## Per-Event Results Table",
        "",
        "| Event ID | Priority | Land Cover | FRP (MW) | Event Date | Pre Date | Pre Status | Post Date | Post Status | Overall Status | Real CDSE |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for _, r in df.iterrows():
        pre_d = str(r.get("selected_pre_image_date", ""))[:10] if pd.notna(r.get("selected_pre_image_date")) and r.get("selected_pre_image_date") else "None"
        post_d = str(r.get("selected_post_image_date", ""))[:10] if pd.notna(r.get("selected_post_image_date")) and r.get("selected_post_image_date") else "None"
        is_real_str = "YES" if r.get("is_real_cdse_data") else "NO"
        lines.append(
            f"| `{r['event_id']}` | {r.get('candidate_priority')} | {r.get('landcover_class')} | "
            f"{r.get('frp', np.nan):.2f} | {r.get('acq_date')} | {pre_d} | `{r.get('pre_observation_status')}` | "
            f"{post_d} | `{r.get('post_observation_status')}` | `{r.get('processing_status')}` | {is_real_str} |"
        )

    lines.extend([
        "",
        "## Quality and Science Verification",
        "",
        "1. **Optical vs Thermal Constraint:** Sentinel-2 Level-2A data measures surface reflectance (VNIR/SWIR) and SCL ground quality. It is strictly optical and does not measure active fire heat.",
        "2. **Zero Synthetic Substitution:** No synthetic or surrogate pixels were substituted for missing or cloud-obscured observations.",
        "3. **Strict Credential Masking:** No client credentials or access tokens were logged or persisted.",
        "",
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")


def run_batch_10():
    start_time = time.time()
    config = Config.load()
    input_csv = config.output_dir / "ground_truth_investigation" / "validation_candidates_v2.csv"
    if not input_csv.exists():
        raise FileNotFoundError(f"Authoritative 633-event dataset not found at: {input_csv}")

    # 1. Deterministic selection of exactly 10 events
    sample_10 = select_10_representative_events(input_csv)
    if len(sample_10) != 10:
        raise ValueError(f"Expected exactly 10 events, got {len(sample_10)}")

    output_dir = config.output_dir / "sentinel2_batch_10"
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    processor = Sentinel2ScaleProcessor(cache_dir=cache_dir)
    has_creds, cred_msg = processor.check_authentication()
    if not has_creds:
        raise RuntimeError("CDSE credentials not found in environment variables.")

    records: List[Dict[str, Any]] = []
    total = len(sample_10)
    logger.info("Starting controlled 10-event real Sentinel-2 batch...")

    for i, (_, row) in enumerate(sample_10.iterrows(), start=1):
        ev_id = str(row["event_id"])
        logger.info("[%d/%d] Processing event %s (Date: %s, Lat: %.5f, Lon: %.5f)...",
                    i, total, ev_id, row["acq_date"], row["latitude"], row["longitude"])
        
        rec = processor.process_event(row)
        combined_rec = {**row.to_dict(), **rec}
        records.append(combined_rec)
        
        logger.info("[%d/%d] Finished %s -> Status: %s, Real CDSE: %s",
                    i, total, ev_id, rec["processing_status"], rec["is_real_cdse_data"])

    df_out = pd.DataFrame(records)
    total_runtime_s = time.time() - start_time

    # Save outputs
    csv_path = output_dir / "sentinel2_batch_10_events.csv"
    df_out.to_csv(csv_path, index=False)
    logger.info("Saved batch CSV: %s (%d rows)", csv_path, len(df_out))

    # Compute metrics for report
    total_events = len(df_out)
    real_success_full = int((df_out["processing_status"] == STATUS_REAL_CDSE_SUCCESS).sum())
    partial_pre = int((df_out["processing_status"] == STATUS_PARTIAL_PRE_ONLY).sum())
    partial_post = int((df_out["processing_status"] == STATUS_PARTIAL_POST_ONLY).sum())
    real_cdse_any = int((df_out["is_real_cdse_data"] == True).sum())

    missing_pre = int((df_out["pre_observation_status"] == STATUS_MISSING_PRODUCT).sum())
    missing_post = int((df_out["post_observation_status"] == STATUS_MISSING_PRODUCT).sum())
    missing_both = int(((df_out["pre_observation_status"] == STATUS_MISSING_PRODUCT) &
                        (df_out["post_observation_status"] == STATUS_MISSING_PRODUCT)).sum())

    insufficient_valid_events = int((df_out["processing_status"] == STATUS_CLOUD_REJECTED).sum())
    insufficient_pre = int((df_out["pre_observation_status"] == STATUS_CLOUD_REJECTED).sum())
    insufficient_post = int((df_out["post_observation_status"] == STATUS_CLOUD_REJECTED).sum())

    auth_failures = int(((df_out["processing_status"] == STATUS_AUTH_REQUIRED) |
                         (df_out["processing_status"] == "AUTH_FAILURE")).sum())
    api_failures = int((df_out["processing_status"] == STATUS_PROCESSING_API_ERROR).sum())
    other_failures = int(((df_out["processing_status"] == STATUS_CORRUPT_RASTER) |
                          (df_out["processing_status"] == "PROCESSING_FAILED")).sum())

    coverage_pct = (real_cdse_any / total_events) * 100.0 if total_events > 0 else 0.0

    successful_feature_records = int(df_out["s2_pre_ndvi_mean"].notna().sum() + df_out["s2_post_ndvi_mean"].notna().sum())
    events_with_change_feats = int((df_out["s2_change_status"] == "SUCCESS").sum())

    all_dates = []
    for d in df_out["selected_pre_image_date"].dropna():
        s = str(d).strip()
        if s and s.lower() not in ("none", "nan"):
            all_dates.append(s[:10])
    for d in df_out["selected_post_image_date"].dropna():
        s = str(d).strip()
        if s and s.lower() not in ("none", "nan"):
            all_dates.append(s[:10])
    
    obs_date_range = f"{min(all_dates)} to {max(all_dates)}" if all_dates else "None"

    metrics = {
        "total_events": total_events,
        "real_success_full": real_success_full,
        "partial_pre": partial_pre,
        "partial_post": partial_post,
        "real_cdse_any": real_cdse_any,
        "missing_pre": missing_pre,
        "missing_post": missing_post,
        "missing_both": missing_both,
        "insufficient_valid_events": insufficient_valid_events,
        "insufficient_pre": insufficient_pre,
        "insufficient_post": insufficient_post,
        "auth_failures": auth_failures,
        "api_failures": api_failures,
        "other_failures": other_failures,
        "coverage_pct": coverage_pct,
        "successful_feature_records": successful_feature_records,
        "events_with_change_feats": events_with_change_feats,
        "obs_date_range": obs_date_range,
        "total_runtime_s": total_runtime_s,
    }

    report_path = output_dir / "SENTINEL2_BATCH_10_REPORT.md"
    generate_batch_report(df_out, report_path, metrics)
    logger.info("Saved batch report: %s", report_path)

    return df_out, metrics


if __name__ == "__main__":
    df_out, metrics = run_batch_10()
    print("\n================== BATCH 10 EXECUTION SUMMARY ==================")
    for k, v in metrics.items():
        print(f" - {k}: {v}")
    print("=================================================================\n")
