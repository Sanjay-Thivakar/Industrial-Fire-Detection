"""Unit and integration tests for Phase 4B: Human Ground-Truth Audit and ML Dataset Preparation."""

from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAL_CSV = PROJECT_ROOT / "outputs" / "ground_truth_investigation" / "validation_batch_v1_100_validated.csv"
MASTER_CSV = PROJECT_ROOT / "outputs" / "phase_4a_dataset_audit" / "sentinel2_master_633_human_merged.csv"
OUT_DIR = PROJECT_ROOT / "outputs" / "phase_4b_ground_truth"
AUDITED_100_CSV = OUT_DIR / "human_validation_audited_100.csv"
ML_LABELLED_CSV = OUT_DIR / "ml_labelled_dataset.csv"
MERGED_633_CSV = OUT_DIR / "sentinel2_master_633_human_ground_truth.csv"
REPORT_MD = OUT_DIR / "PHASE_4B_GROUND_TRUTH_REPORT.md"

OFFICIAL_CLASSES = {
    "Industrial Fire",
    "Persistent Industrial Thermal Source",
    "Agricultural Burning",
    "Natural/Forest Fire",
    "Other/Unclassified",
    "Unknown/Insufficient Evidence",
}


def test_audited_100_structure():
    """Verify the audited 100-record dataset."""
    assert AUDITED_100_CSV.exists(), f"File missing: {AUDITED_100_CSV}"
    df = pd.read_csv(AUDITED_100_CSV)
    assert len(df) == 100, f"Expected 100 rows, got {len(df)}"
    assert df["event_id"].nunique() == 100, "Duplicate event IDs found"
    assert df["event_id"].isna().sum() == 0, "Missing event IDs found"

    # All classes either in OFFICIAL_CLASSES or REVIEW_REQUIRED
    allowed_classes = OFFICIAL_CLASSES.union({"REVIEW_REQUIRED"})
    assert set(df["normalized_official_class"].unique()).issubset(allowed_classes)

    # 76 unambiguous, 24 review required
    assert (df["is_unambiguous"] == True).sum() == 76
    assert (df["is_unambiguous"] == False).sum() == 24


def test_ml_labelled_dataset():
    """Verify ML-ready labelled dataset."""
    assert ML_LABELLED_CSV.exists(), f"File missing: {ML_LABELLED_CSV}"
    df = pd.read_csv(ML_LABELLED_CSV)
    assert len(df) == 76, f"Expected exactly 76 unambiguous records, got {len(df)}"
    assert df["event_id"].nunique() == 76, "Duplicate event IDs in ML dataset"

    # All labels must be in OFFICIAL_CLASSES (no REVIEW_REQUIRED in ML dataset)
    assert set(df["human_ground_truth_class"].unique()).issubset(OFFICIAL_CLASSES)

    # Check class counts
    counts = df["human_ground_truth_class"].value_counts().to_dict()
    assert counts.get("Agricultural Burning", 0) == 50
    assert counts.get("Persistent Industrial Thermal Source", 0) == 12
    assert counts.get("Natural/Forest Fire", 0) == 9
    assert counts.get("Industrial Fire", 0) == 3
    assert counts.get("Other/Unclassified", 0) == 2


def test_merged_633_integrity():
    """Verify the full 633-event merged dataset."""
    assert MERGED_633_CSV.exists(), f"File missing: {MERGED_633_CSV}"
    df = pd.read_csv(MERGED_633_CSV)
    assert len(df) == 633, f"Expected 633 rows, got {len(df)}"
    assert df["event_id"].nunique() == 633, "Duplicate event IDs in merged dataset"

    # 100 with human validation, 533 without
    assert df["has_human_validation"].sum() == 100
    assert (~df["has_human_validation"]).sum() == 533

    # Only 76 eligible for ML
    assert df["ml_training_eligible"].sum() == 76

    # 533 unreviewed must have NaN ground truth class
    unreviewed = df[df["has_human_validation"] == False]
    assert unreviewed["human_ground_truth_class"].isna().sum() == 533
    assert (unreviewed["human_validation_status"] == "UNREVIEWED").sum() == 533


def test_report_exists_and_content():
    """Verify Phase 4B report content."""
    assert REPORT_MD.exists(), f"Report missing: {REPORT_MD}"
    content = REPORT_MD.read_text(encoding="utf-8")
    assert "Phase 4B: Human Ground-Truth Audit" in content
    assert "76 records" in content
    assert "24 records" in content
    assert "Definitive Answer: NO" in content
