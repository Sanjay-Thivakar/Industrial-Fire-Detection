"""Unit and integration tests for Phase 4C: Final 3-Class ML Feature Preparation."""

from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "outputs" / "phase_4c_ml"
DATASET_PATH = OUT_DIR / "ml_3class_dataset.csv"
BASELINE_MANIFEST_PATH = OUT_DIR / "feature_manifest_baseline.csv"
S2_MANIFEST_PATH = OUT_DIR / "feature_manifest_sentinel2.csv"
REPORT_PATH = OUT_DIR / "PHASE_4C_ML_PREPARATION_REPORT.md"
SOURCE_ML_PATH = PROJECT_ROOT / "outputs" / "phase_4b_ground_truth" / "ml_labelled_dataset.csv"

EXPECTED_3CLASS_COUNTS = {
    "Agricultural Burning": 50,
    "Industrial Thermal Activity": 15,
    "Natural / Wildfire / Other": 11,
}


def test_artifacts_exist():
    """Verify all Phase 4C artifacts exist."""
    assert DATASET_PATH.exists(), f"Missing dataset: {DATASET_PATH}"
    assert BASELINE_MANIFEST_PATH.exists(), f"Missing baseline manifest: {BASELINE_MANIFEST_PATH}"
    assert S2_MANIFEST_PATH.exists(), f"Missing S2 manifest: {S2_MANIFEST_PATH}"
    assert REPORT_PATH.exists(), f"Missing report: {REPORT_PATH}"


def test_dataset_integrity():
    """Verify row count, 3-class target, and uniqueness."""
    df = pd.read_csv(DATASET_PATH)
    assert len(df) == 76, f"Expected 76 rows, got {len(df)}"
    assert df["event_id"].nunique() == 76, "Duplicate event IDs found"
    assert df["event_id"].isna().sum() == 0, "Missing event IDs found"

    # Check target
    assert "ml_target_3class" in df.columns
    counts = df["ml_target_3class"].value_counts().to_dict()
    assert counts == EXPECTED_3CLASS_COUNTS, f"3-Class counts mismatch: {counts}"

    # Verify no REVIEW_REQUIRED
    assert (df["ml_target_3class"] == "REVIEW_REQUIRED").sum() == 0
    assert (df["human_ground_truth_class"] == "REVIEW_REQUIRED").sum() == 0


def test_feature_manifests():
    """Verify baseline and Sentinel-2 feature manifests."""
    base_df = pd.read_csv(BASELINE_MANIFEST_PATH)
    s2_df = pd.read_csv(S2_MANIFEST_PATH)

    assert len(base_df) == 36, f"Expected 36 baseline features, got {len(base_df)}"
    assert len(s2_df) == 73, f"Expected 73 S2 features, got {len(s2_df)}"

    # All baseline features must be subset of S2 features
    base_features = set(base_df["feature_name"])
    s2_features = set(s2_df["feature_name"])
    assert base_features.issubset(s2_features)

    # All features must exist in dataset
    dataset_df = pd.read_csv(DATASET_PATH)
    for feat in s2_features:
        assert feat in dataset_df.columns, f"Feature {feat} missing from dataset"


def test_no_target_leakage():
    """Verify that target leakage and identifier columns are not in feature manifests."""
    s2_df = pd.read_csv(S2_MANIFEST_PATH)
    features = set(s2_df["feature_name"])

    leakage_columns = [
        "ml_target_3class",
        "human_ground_truth_class",
        "human_raw_label",
        "weak_label",
        "ground_truth_status",
        "human_validation_status",
        "human_industry_observation",
        "candidate_priority",
        "candidate_priority_score",
        "event_id",
        "row_id",
    ]
    for leak in leakage_columns:
        assert leak not in features, f"Target leakage detected in features: {leak}"


def test_cross_validation_folds():
    """Verify stratified 5-fold cross-validation distribution."""
    df = pd.read_csv(DATASET_PATH)
    assert "cv_fold_5" in df.columns
    assert set(df["cv_fold_5"].unique()) == {0, 1, 2, 3, 4}

    # Verify each fold has representation of each class
    for fold in range(5):
        fold_df = df[df["cv_fold_5"] == fold]
        counts = fold_df["ml_target_3class"].value_counts().to_dict()
        assert counts.get("Industrial Thermal Activity", 0) == 3
        assert counts.get("Agricultural Burning", 0) == 10
        assert counts.get("Natural / Wildfire / Other", 0) in [2, 3]


def test_missingness_indicators():
    """Verify that missingness indicators are properly binary."""
    df = pd.read_csv(DATASET_PATH)
    for col in ["s2_pre_missing", "s2_post_missing", "s2_change_missing"]:
        assert col in df.columns
        assert set(df[col].unique()).issubset({0, 1})
