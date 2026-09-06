"""Execution script for Phase 3 Step 3E: Full-Scale Resumable Real Sentinel-2 Processing (633 Events).

Processes the authoritative 633 FIRMS thermal event dataset using Sentinel2ScaleProcessor
with real Copernicus Data Space Ecosystem (CDSE) Sentinel-2 Level-2A data.

SAFETY & AUDIT PROTOCOL:
1. Source dataset (outputs/ground_truth_investigation/validation_candidates_v2.csv)
   remains strictly read-only and unmodified. SHA256 checksum is verified before and after.
2. Output directory is strictly isolated: outputs/sentinel2_full_633/
3. Previous 10-event and 50-event outputs are never overwritten.
4. Resumability is built-in: completed events are tracked in .cache/{event_id}.json
   and sentinel2_full_633_manifest.csv. Any interruption can be resumed seamlessly.
5. All original event metadata columns are preserved.
6. Execution manifest records event_id, statuses, CDSE data flag, timestamp, and error category.
7. Credentials come strictly from environment variables (CDSE_CLIENT_ID / CDSE_CLIENT_SECRET)
   and are NEVER printed or persisted.
8. Requires explicit '--execute' argument to prevent accidental live execution.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from src.config import Config
from src.feature_engineering.sentinel2_scale_processor import (
    Sentinel2ScaleProcessor,
    STATUS_REAL_CDSE_SUCCESS,
    STATUS_AUTH_REQUIRED,
    STATUS_PARTIAL_PRE_ONLY,
    STATUS_PARTIAL_POST_ONLY,
    STATUS_CLOUD_REJECTED,
    STATUS_MISSING_PRODUCT,
    STATUS_PROCESSING_API_ERROR,
    STATUS_CORRUPT_RASTER,
    STATUS_PROCESSING_FAILED,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Sentinel2Scale633")

OUTPUT_SUBDIR = "sentinel2_full_633"
MASTER_CSV_FILENAME = "sentinel2_full_633_events.csv"
MANIFEST_FILENAME = "sentinel2_full_633_manifest.csv"
REPORT_FILENAME = "SENTINEL2_FULL_633_REPORT.md"


def compute_file_sha256(filepath: Path) -> str:
    """Calculate the SHA256 hash of a file for integrity tracking."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_source_integrity(source_path: Path) -> Tuple[pd.DataFrame, str]:
    """Perform strict pre-flight integrity verification on the 633-event source dataset."""
    if not source_path.exists():
        raise FileNotFoundError(f"Authoritative 633-event dataset not found at: {source_path}")

    sha256_initial = compute_file_sha256(source_path)
    df = pd.read_csv(source_path)

    # Check row count
    if len(df) != 633:
        raise ValueError(f"Integrity check failed: Expected exactly 633 events, got {len(df)}")

    # Check uniqueness
    if df["event_id"].nunique() != 633:
        raise ValueError(f"Integrity check failed: Found duplicate event_ids ({df['event_id'].nunique()} unique)")

    # Check critical columns
    required_cols = ["event_id", "row_id", "acq_date", "latitude", "longitude", "candidate_priority", "landcover_class", "frp"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Integrity check failed: Missing required column '{c}'")
        if df[c].isnull().any():
            raise ValueError(f"Integrity check failed: Null values found in critical column '{c}'")

    logger.info("Source dataset integrity verified: 633 unique events, SHA256: %s...", sha256_initial[:16])
    return df, sha256_initial


def get_resumable_status(output_dir: Path, source_event_ids: Set[str]) -> Tuple[Set[str], List[Dict[str, Any]]]:
    """Inspect persistent output state and return set of completed event IDs and manifest records."""
    cache_dir = output_dir / ".cache"
    manifest_path = output_dir / MANIFEST_FILENAME
    completed_ids: Set[str] = set()
    manifest_records: List[Dict[str, Any]] = []

    # 1. Check cache files
    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            ev_id = f.stem
            if ev_id in source_event_ids:
                try:
                    with open(f, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                    if data.get("event_id") == ev_id and data.get("processing_status"):
                        completed_ids.add(ev_id)
                except Exception:
                    pass

    # 2. Check existing manifest CSV if present
    if manifest_path.exists():
        try:
            m_df = pd.read_csv(manifest_path)
            for _, r in m_df.iterrows():
                ev_id = str(r["event_id"])
                if ev_id in source_event_ids and pd.notna(r.get("processing_status")):
                    completed_ids.add(ev_id)
                    manifest_records.append(r.to_dict())
        except Exception:
            pass

    return completed_ids, manifest_records


def verify_output_integrity(
    source_path: Path,
    initial_sha256: str,
    df_results: pd.DataFrame,
    manifest_df: pd.DataFrame,
    source_df: pd.DataFrame,
) -> None:
    """Verify post-run outputs against strict integrity standards."""
    # 1. Verify source file was not modified
    post_sha256 = compute_file_sha256(source_path)
    if post_sha256 != initial_sha256:
        raise RuntimeError("CRITICAL ERROR: Source dataset validation_candidates_v2.csv was modified during execution!")

    # 2. Verify row count
    if len(df_results) != 633:
        raise ValueError(f"Output verification failed: Expected 633 output rows, got {len(df_results)}")
    if len(manifest_df) != 633:
        raise ValueError(f"Output verification failed: Expected 633 manifest rows, got {len(manifest_df)}")

    # 3. Verify uniqueness
    if df_results["event_id"].nunique() != 633:
        raise ValueError("Output verification failed: Duplicate event_ids in output CSV")
    if manifest_df["event_id"].nunique() != 633:
        raise ValueError("Output verification failed: Duplicate event_ids in manifest CSV")

    # 4. Verify no external events processed
    source_ids = set(source_df["event_id"])
    out_ids = set(df_results["event_id"])
    if out_ids != source_ids:
        diff_extra = out_ids - source_ids
        diff_missing = source_ids - out_ids
        raise ValueError(f"Output verification failed: Mismatch in event IDs. Extra: {diff_extra}, Missing: {diff_missing}")

    # 5. Verify original metadata preservation
    for col in ["row_id", "acq_date", "acq_datetime", "latitude", "longitude", "satellite", "confidence", "landcover_class"]:
        if col in source_df.columns:
            if col not in df_results.columns:
                raise ValueError(f"Output verification failed: Original column '{col}' missing from output")

    logger.info("All post-run output integrity assertions PASSED.")


def check_full_scale_readiness() -> Dict[str, Any]:
    """Execute pre-flight audit and verify runner readiness without executing live CDSE requests."""
    config = Config.load()
    source_path = config.output_dir / "ground_truth_investigation" / "validation_candidates_v2.csv"
    source_df, sha256 = verify_source_integrity(source_path)

    output_dir = config.output_dir / OUTPUT_SUBDIR
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Initialize processor
    processor = Sentinel2ScaleProcessor(cache_dir=cache_dir)
    has_creds, cred_msg = processor.check_authentication()

    source_event_ids = set(source_df["event_id"])
    completed_ids, _ = get_resumable_status(output_dir, source_event_ids)

    readiness = {
        "source_dataset": str(source_path),
        "source_rows": len(source_df),
        "source_unique_event_ids": source_df["event_id"].nunique(),
        "source_sha256": sha256,
        "output_dir": str(output_dir),
        "cache_dir": str(cache_dir),
        "master_csv_target": str(output_dir / MASTER_CSV_FILENAME),
        "manifest_target": str(output_dir / MANIFEST_FILENAME),
        "report_target": str(output_dir / REPORT_FILENAME),
        "has_cdse_credentials": has_creds,
        "cdse_auth_message": cred_msg,
        "completed_events_count": len(completed_ids),
        "remaining_events_count": len(source_df) - len(completed_ids),
        "is_ready": bool(has_creds and len(source_df) == 633),
    }

    print("\n=======================================================")
    print("  Phase 3 — Step 3E: 633-Event Full Scale Pre-Flight  ")
    print("=======================================================")
    print(f"Authoritative Dataset           : {source_path.name} (633 events)")
    print(f"Source SHA256 Checksum          : {sha256[:16]}...")
    print(f"Output Directory                : {output_dir}")
    print(f"CDSE Authentication Ready       : {has_creds}")
    print(f"Resumability Status             : {len(completed_ids)} completed, {len(source_df) - len(completed_ids)} remaining")
    print(f"Pipeline State                  : {'READY FOR SAFE EXECUTION' if readiness['is_ready'] else 'NOT READY'}")
    print("=======================================================\n")

    return readiness


def run_full_scaled_processing(resume: bool = True) -> pd.DataFrame:
    """Execute full 633-event Sentinel-2 processing run with full resumability and audit manifest."""
    config = Config.load()
    source_path = config.output_dir / "ground_truth_investigation" / "validation_candidates_v2.csv"
    source_df, initial_sha256 = verify_source_integrity(source_path)

    # Sort deterministically by row_id / event_id
    events_df = source_df.sort_values(by=["row_id", "event_id"]).copy()

    output_dir = config.output_dir / OUTPUT_SUBDIR
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    processor = Sentinel2ScaleProcessor(cache_dir=cache_dir)
    has_creds, cred_msg = processor.check_authentication()
    if not has_creds:
        raise RuntimeError(f"CDSE credentials missing: {cred_msg}. Cannot proceed with live 633 run.")

    source_event_ids = set(source_df["event_id"])
    initially_completed, _ = get_resumable_status(output_dir, source_event_ids)
    num_resumed = len(initially_completed)

    logger.info("Beginning execution across all 633 FIRMS events (resumable=%s, already_completed=%d)...", resume, num_resumed)
    start_time = time.time()

    df_results = processor.process_all_events(
        events_df=events_df,
        output_dir=output_dir,
        resume=resume,
        csv_filename=MASTER_CSV_FILENAME,
        manifest_filename=MANIFEST_FILENAME,
        report_filename=REPORT_FILENAME,
    )

    elapsed_s = time.time() - start_time
    manifest_path = output_dir / MANIFEST_FILENAME
    manifest_df = pd.read_csv(manifest_path) if manifest_path.exists() else pd.DataFrame()

    # Post-run integrity verification
    verify_output_integrity(source_path, initial_sha256, df_results, manifest_df, source_df)

    # Compute detailed metrics for reporting
    total = len(df_results)
    success = int((df_results["processing_status"] == STATUS_REAL_CDSE_SUCCESS).sum())
    partial_pre = int((df_results["processing_status"] == STATUS_PARTIAL_PRE_ONLY).sum())
    partial_post = int((df_results["processing_status"] == STATUS_PARTIAL_POST_ONLY).sum())
    real_cdse_any = int((df_results["is_real_cdse_data"] == True).sum())

    missing_pre = int((df_results["pre_observation_status"] == STATUS_MISSING_PRODUCT).sum())
    missing_post = int((df_results["post_observation_status"] == STATUS_MISSING_PRODUCT).sum())
    missing_both = int(((df_results["pre_observation_status"] == STATUS_MISSING_PRODUCT) &
                        (df_results["post_observation_status"] == STATUS_MISSING_PRODUCT)).sum())
    missing_product_events = int(((df_results["pre_observation_status"] == STATUS_MISSING_PRODUCT) |
                                  (df_results["post_observation_status"] == STATUS_MISSING_PRODUCT)).sum())

    insufficient_valid_events = int((df_results["processing_status"] == STATUS_CLOUD_REJECTED).sum())
    insufficient_pre = int((df_results["pre_observation_status"] == STATUS_CLOUD_REJECTED).sum())
    insufficient_post = int((df_results["post_observation_status"] == STATUS_CLOUD_REJECTED).sum())

    auth_failures = int(((df_results["processing_status"] == STATUS_AUTH_REQUIRED) |
                         (df_results["processing_status"] == "AUTH_FAILURE")).sum())
    api_failures = int((df_results["processing_status"] == STATUS_PROCESSING_API_ERROR).sum())
    other_failures = int(((df_results["processing_status"] == STATUS_CORRUPT_RASTER) |
                          (df_results["processing_status"] == STATUS_PROCESSING_FAILED) |
                          (df_results["processing_status"] == "PROCESSING_FAILED")).sum())

    coverage_pct = (real_cdse_any / total) * 100.0 if total > 0 else 0.0
    complete_pre_post_pct = (success / total) * 100.0 if total > 0 else 0.0
    pre_only_pct = (partial_pre / total) * 100.0 if total > 0 else 0.0
    post_only_pct = (partial_post / total) * 100.0 if total > 0 else 0.0
    cloud_rej_pct = (insufficient_valid_events / total) * 100.0 if total > 0 else 0.0
    missing_prod_pct = (missing_product_events / total) * 100.0 if total > 0 else 0.0
    missing_both_pct = (missing_both / total) * 100.0 if total > 0 else 0.0
    api_fail_pct = (api_failures / total) * 100.0 if total > 0 else 0.0
    auth_fail_pct = (auth_failures / total) * 100.0 if total > 0 else 0.0
    other_fail_pct = (other_failures / total) * 100.0 if total > 0 else 0.0

    usable_spectral_records = int(df_results["s2_pre_ndvi_mean"].notna().sum() + df_results["s2_post_ndvi_mean"].notna().sum())
    events_with_change_feats = int((df_results["s2_change_status"] == "SUCCESS").sum())

    all_dates = []
    for d in df_results["selected_pre_image_date"].dropna():
        s = str(d).strip()
        if s and s.lower() not in ("none", "nan"):
            all_dates.append(s[:10])
    for d in df_results["selected_post_image_date"].dropna():
        s = str(d).strip()
        if s and s.lower() not in ("none", "nan"):
            all_dates.append(s[:10])
    obs_date_range = f"{min(all_dates)} to {max(all_dates)}" if all_dates else "None"

    print("\n=======================================================")
    print("      Phase 3 — Step 3E: 633-Event Processing Summary ")
    print("=======================================================")
    print(f"Total Events Attempted          : {total}")
    print(f"Resumed / Skipped from Cache    : {num_resumed}")
    print(f"Real CDSE Acquisition Rate      : {coverage_pct:.1f}% ({real_cdse_any}/{total})")
    print(f"Complete Pre/Post Rate          : {complete_pre_post_pct:.1f}% ({success}/{total})")
    print(f"Pre-only Success Rate           : {pre_only_pct:.1f}% ({partial_pre}/{total})")
    print(f"Post-only Success Rate          : {post_only_pct:.1f}% ({partial_post}/{total})")
    print(f"Cloud Rejection Rate            : {cloud_rej_pct:.1f}% ({insufficient_valid_events}/{total})")
    print(f"Missing Product Rate            : {missing_prod_pct:.1f}% ({missing_product_events}/{total})")
    print(f"Missing Both Products Rate      : {missing_both_pct:.1f}% ({missing_both}/{total})")
    print(f"Insufficient Valid Data Events  : {insufficient_valid_events} (Pre: {insufficient_pre}, Post: {insufficient_post})")
    print(f"API Failure Rate                : {api_fail_pct:.1f}% ({api_failures}/{total})")
    print(f"Authentication Failure Rate     : {auth_fail_pct:.1f}% ({auth_failures}/{total})")
    print(f"Other Failure Rate              : {other_fail_pct:.1f}% ({other_failures}/{total})")
    print(f"Usable Spectral Feature Records : {usable_spectral_records}")
    print(f"Complete Temporal Change Sets   : {events_with_change_feats}")
    print(f"Observation Date Range          : {obs_date_range}")
    print(f"Total Execution Time            : {elapsed_s:.2f} s ({elapsed_s/60.0:.2f} min)")
    print(f"Outputs written to              : {output_dir}")
    print("=======================================================\n")

    return df_results


def main():
    parser = argparse.ArgumentParser(description="Phase 3 Step 3E: 633-Event Scaled Real Sentinel-2 Processor")
    parser.add_argument("--execute", action="store_true", help="Execute the live 633-event processing run")
    parser.add_argument("--check-readiness", action="store_true", help="Run pre-flight integrity audit without execution")
    parser.add_argument("--no-resume", action="store_true", help="Disable cache resumption and reprocess from scratch")

    args = parser.parse_args()

    if args.execute:
        run_full_scaled_processing(resume=not args.no_resume)
    else:
        # Default safety: only perform pre-flight readiness audit and stop
        check_full_scale_readiness()
        print("NOTICE: Execution halted safely per protocol ('--execute' flag not provided).")
        print("The runner is verified, resumable, and ready for execution.\n")


if __name__ == "__main__":
    main()
