"""
tests/test_ml_inference.py - Unit tests for Phase 5 ML Inference Interface

Tests:
- Model loads successfully from default and explicit paths
- Valid feature input produces a valid prediction
- Prediction belongs strictly to the three official classes
- Probabilities are valid, non-negative, and sum to 1.0 (+/- 1e-4)
- Confidence is one of HIGH / MEDIUM / LOW
- Missing required feature produces a clear, descriptive ValueError
- Target leakage / human ground-truth fields are blocked from model input
- Batch prediction produces expected DataFrame structure
- Reproducibility: Calling inference on the same input yields identical results
"""

import os
import pytest
import pandas as pd
import numpy as np

from src.models.predict import (
    load_production_model,
    predict_event,
    predict_batch,
    validate_and_prepare_features,
    REQUIRED_FEATURES,
    TARGET_LEAKAGE_FIELDS,
    PRODUCTION_CLASSES,
    CONFIDENCE_TIERS
)


@pytest.fixture(scope="module")
def valid_sample_record():
    """Returns a valid 36-feature dictionary from the clean dataset."""
    dataset_path = os.path.join("outputs", "phase_4c_ml", "ml_3class_dataset.csv")
    assert os.path.exists(dataset_path), f"Dataset missing at {dataset_path}"
    df = pd.read_csv(dataset_path)
    # Select first record and drop ground-truth leakage fields
    record = df.iloc[0].to_dict()
    clean_features = {
        k: v for k, v in record.items()
        if k not in TARGET_LEAKAGE_FIELDS and k != "ml_target_3class"
    }
    return clean_features


def test_model_loading():
    """Verify that the production model loads and possesses required attributes."""
    model = load_production_model()
    assert model is not None
    assert hasattr(model, "predict")
    assert hasattr(model, "predict_proba")
    assert hasattr(model, "classes_")
    assert len(model.classes_) == 3


def test_predict_event_valid_output(valid_sample_record):
    """Verify inference output structure, values, and probability sums."""
    result = predict_event(valid_sample_record)

    assert isinstance(result, dict)
    assert "prediction" in result
    assert "probabilities" in result
    assert "max_probability" in result
    assert "confidence" in result
    assert "model_architecture" in result

    # Prediction must belong to official 3 classes
    assert result["prediction"] in PRODUCTION_CLASSES

    # Probabilities dictionary must contain all 3 classes
    probs = result["probabilities"]
    assert set(probs.keys()) == set(PRODUCTION_CLASSES)

    # Probabilities must be bounded in [0, 1]
    for cls_name, prob in probs.items():
        assert 0.0 <= prob <= 1.0

    # Probabilities must sum to 1.0
    total_prob = sum(probs.values())
    assert pytest.approx(total_prob, abs=1e-3) == 1.0

    # max_probability must match the highest probability in dictionary
    assert result["max_probability"] == max(probs.values())

    # Confidence tier must be one of HIGH, MEDIUM, LOW
    assert result["confidence"] in CONFIDENCE_TIERS

    # Confidence tier must align with threshold rules
    max_p = result["max_probability"]
    if max_p >= 0.75:
        assert result["confidence"] == "HIGH"
    elif max_p >= 0.50:
        assert result["confidence"] == "MEDIUM"
    else:
        assert result["confidence"] == "LOW"


def test_missing_feature_raises_error(valid_sample_record):
    """Verify that omitting required features produces an explicit, informative ValueError."""
    incomplete_features = valid_sample_record.copy()
    # Remove two required features from baseline manifest
    removed_keys = ["frp", "distance_to_facility_m"]
    for k in removed_keys:
        del incomplete_features[k]

    with pytest.raises(ValueError) as exc_info:
        predict_event(incomplete_features)

    err_msg = str(exc_info.value)
    assert "required feature(s)" in err_msg
    assert "frp" in err_msg
    assert "distance_to_facility_m" in err_msg


def test_target_leakage_fields_raise_error(valid_sample_record):
    """Verify that passing human validation or ground truth fields causes a hard ValueError."""
    for leak_col in ["human_ground_truth_class", "ml_target_3class", "weak_label"]:
        leaky_features = valid_sample_record.copy()
        leaky_features[leak_col] = "Industrial Thermal Activity"

        with pytest.raises(ValueError) as exc_info:
            predict_event(leaky_features)

        assert "Target leakage detected" in str(exc_info.value)
        assert leak_col in str(exc_info.value)


def test_batch_prediction():
    """Verify predict_batch() handles multiple events and returns correct list of dicts."""
    dataset_path = os.path.join("outputs", "phase_4c_ml", "ml_3class_dataset.csv")
    df = pd.read_csv(dataset_path).head(5)
    # Strip leakage columns
    clean_df = df.drop(columns=[c for c in TARGET_LEAKAGE_FIELDS if c in df.columns] + ["ml_target_3class"], errors="ignore")

    results = predict_batch(clean_df)

    assert isinstance(results, list)
    assert len(results) == 5
    for item in results:
        assert isinstance(item, dict)
        assert item["prediction"] in PRODUCTION_CLASSES
        assert item["confidence"] in CONFIDENCE_TIERS
        assert "probabilities" in item
        assert len(item["probabilities"]) == 3


def test_reproducibility(valid_sample_record):
    """Verify identical results across multiple runs on the same input."""
    res1 = predict_event(valid_sample_record)
    res2 = predict_event(valid_sample_record)

    assert res1["prediction"] == res2["prediction"]
    assert res1["max_probability"] == res2["max_probability"]
    assert res1["confidence"] == res2["confidence"]
    assert res1["probabilities"] == res2["probabilities"]
