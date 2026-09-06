"""Unit and integration tests for Phase 4A: Dataset Audit and Human-Label Integration."""

import hashlib
from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_PATH = PROJECT_ROOT / "outputs" / "sentinel2_full_633" / "sentinel2_full_633_events.csv"
BATCH_PATH = PROJECT_ROOT / "outputs" / "ground_truth_investigation" / "validation_batch_v1_100.csv"
OUT_DIR = PROJECT_ROOT / "outputs" / "phase_4a_dataset_audit"
MERGED_PATH = OUT_DIR / "sentinel2_master_633_human_merged.csv"
ML_PATH = OUT_DIR / "ml_ready_human_labelled.csv"
REPORT_PATH = OUT_DIR / "PHASE_4A_DATASET_AUDIT_REPORT.md"


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_master_dataset_integrity():
    """Verify Sentinel-2 master dataset constraints."""
    assert MASTER_PATH.exists(), f"Master dataset not found: {MASTER_PATH}"
    df = pd.read_csv(MASTER_PATH)
    assert len(df) == 633, f"Expected 633 rows, got {len(df)}"
    assert df["event_id"].nunique() == 633, "Duplicate event IDs found in master"
    assert df["event_id"].isna().sum() == 0, "Missing event IDs found in master"

    # Status check
    assert (df["processing_status"] == "PROCESSING_API_ERROR").sum() == 0, "Found residual PROCESSING_API_ERROR"
    assert (df["processing_status"].isin(["AUTH_FAILURE", "AUTH_REQUIRED"])).sum() == 0, "Found residual AUTH_FAILURE"

    # Pre/post observations
    assert df["s2_pre_ndvi_mean"].notna().sum() == 375
    assert df["s2_post_ndvi_mean"].notna().sum() == 364
    assert (df["s2_pre_ndvi_mean"].notna() & df["s2_post_ndvi_mean"].notna()).sum() == 206
    assert (df["processing_status"] == "REAL_CDSE_SUCCESS").sum() == 80


def test_validation_batch_audit():
    """Verify validation batch properties."""
    assert BATCH_PATH.exists(), f"Validation batch not found: {BATCH_PATH}"
    df = pd.read_csv(BATCH_PATH)
    assert len(df) == 100, f"Expected 100 rows, got {len(df)}"
    assert df["event_id"].nunique() == 100, "Duplicate event IDs found in batch"

    # All 100 are UNVERIFIED
    assert (df["ground_truth_status"] == "UNVERIFIED").sum() == 100
    # No human labels column
    assert "validation_label" not in df.columns or df["validation_label"].isna().all()


def test_merged_dataset_integrity():
    """Verify merged master dataset."""
    assert MERGED_PATH.exists(), f"Merged dataset not found: {MERGED_PATH}"
    df = pd.read_csv(MERGED_PATH)
    assert len(df) == 633, f"Expected 633 rows in merged dataset, got {len(df)}"
    assert df["event_id"].nunique() == 633, "Duplicate event IDs in merged dataset"

    # Validation batch flag counts
    assert df["in_validation_batch_100"].sum() == 100
    assert (~df["in_validation_batch_100"]).sum() == 533

    # Zero synthetic label leakage
    assert df["has_human_validation"].sum() == 0, "Unexpected human validation flag set"
    assert df["human_ground_truth_class"].isna().sum() == 633, "Found synthetic label leakage in ground truth"

    # Priority distribution in batch
    batch_rows = df[df["in_validation_batch_100"] == True]
    assert (batch_rows["candidate_priority"] == "HIGH").sum() == 20
    assert (batch_rows["candidate_priority"] == "MEDIUM").sum() == 72
    assert (batch_rows["candidate_priority"] == "LOW").sum() == 8


def test_ml_ready_dataset_integrity():
    """Verify ML-ready dataset contains only verified human labels."""
    assert ML_PATH.exists(), f"ML-ready dataset not found: {ML_PATH}"
    df = pd.read_csv(ML_PATH)
    # Since 0 human labels verified, ML-ready subset has 0 rows
    assert len(df) == 0, "ML-ready dataset should be empty when no verified human labels exist"


def test_report_exists():
    """Verify Phase 4A report was generated."""
    assert REPORT_PATH.exists(), f"Report not found: {REPORT_PATH}"
    content = REPORT_PATH.read_text(encoding="utf-8")
    assert "Phase 4A: Final Dataset Audit" in content
    assert "633 unique FIRMS events" in content
