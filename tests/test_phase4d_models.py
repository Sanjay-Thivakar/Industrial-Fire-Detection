"""Unit and integration tests for Phase 4D: Model Training and Evaluation."""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "outputs" / "phase_4d_models"

MODEL_COMPARISON_PATH = MODELS_DIR / "model_comparison.csv"
CV_RESULTS_PATH = MODELS_DIR / "cross_validation_results.csv"
FINAL_MODEL_PATH = MODELS_DIR / "final_model.joblib"
METADATA_PATH = MODELS_DIR / "final_model_metadata.json"
FEATURE_IMP_PATH = MODELS_DIR / "feature_importance.csv"
CONF_MATRIX_PNG = MODELS_DIR / "confusion_matrix.png"
REPORT_PATH = MODELS_DIR / "PHASE_4D_MODEL_TRAINING_REPORT.md"
DATASET_PATH = PROJECT_ROOT / "outputs" / "phase_4c_ml" / "ml_3class_dataset.csv"
BASE_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "phase_4c_ml" / "feature_manifest_baseline.csv"


def test_artifacts_exist():
    """Verify that all Phase 4D model artifacts exist and have non-zero size."""
    for path in [
        MODEL_COMPARISON_PATH,
        CV_RESULTS_PATH,
        FINAL_MODEL_PATH,
        METADATA_PATH,
        FEATURE_IMP_PATH,
        CONF_MATRIX_PNG,
        REPORT_PATH,
    ]:
        assert path.exists(), f"Artifact missing: {path}"
        assert path.stat().st_size > 0, f"Artifact is empty: {path}"


def test_model_comparison_content():
    """Verify model comparison table contents."""
    df = pd.read_csv(MODEL_COMPARISON_PATH)
    assert len(df) == 6, f"Expected 6 model experiment rows, got {len(df)}"

    experiments = set(df["experiment"].unique())
    assert experiments == {"Baseline", "Sentinel-2 Enhanced"}

    models = set(df["model_name"].unique())
    assert models == {"Random Forest", "Extra Trees", "HistGradientBoosting"}

    # Macro F1 should be > 0.65 for all tree models
    assert (df["macro_f1_oof"] >= 0.65).all()

    # Industrial recall should be high across all models
    assert (df["industrial_recall"] >= 0.90).all()


def test_cross_validation_results():
    """Verify cross validation fold metrics."""
    df = pd.read_csv(CV_RESULTS_PATH)
    assert len(df) == 30, f"Expected 30 fold evaluations (6 models * 5 folds), got {len(df)}"
    assert set(df["fold"].unique()) == {0, 1, 2, 3, 4}


def test_final_model_pipeline_predictive():
    """Verify serialized final model pipeline can be loaded and predict accurately."""
    pipeline = joblib.load(FINAL_MODEL_PATH)
    data_df = pd.read_csv(DATASET_PATH)
    base_manifest = pd.read_csv(BASE_MANIFEST_PATH)
    feature_cols = base_manifest["feature_name"].tolist()

    X = data_df[feature_cols]
    preds = pipeline.predict(X)

    assert len(preds) == len(data_df)
    assert set(preds).issubset({
        "Industrial Thermal Activity",
        "Agricultural Burning",
        "Natural / Wildfire / Other",
    })

    # Industrial recall on training set should be >= 0.90
    y = data_df["ml_target_3class"]
    ind_true = y == "Industrial Thermal Activity"
    ind_pred = preds == "Industrial Thermal Activity"
    ind_recall = (ind_true & ind_pred).sum() / ind_true.sum()
    assert ind_recall >= 0.90, f"Industrial recall {ind_recall} too low"


def test_metadata_consistency():
    """Verify metadata json values match model comparison table."""
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["selected_model_name"] == "Random Forest"
    assert meta["experiment"] == "Baseline"
    assert meta["industrial_recall"] >= 0.90
    assert meta["macro_f1_oof"] >= 0.75
    assert meta["training_samples"] == 76
    assert meta["features_count"] == 36


def test_feature_importance():
    """Verify feature importance file."""
    df = pd.read_csv(FEATURE_IMP_PATH)
    assert len(df) > 36, "Transformed features count too low"
    assert np.isclose(df["importance"].sum(), 1.0, atol=1e-3), "Feature importances do not sum to 1"
    # Persistence features should be near top
    top_features = df.head(10)["feature"].tolist()
    assert any("grid" in f for f in top_features), "Expected grid persistence feature in top 10"
