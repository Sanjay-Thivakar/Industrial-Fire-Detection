"""Unit and integration tests for the Phase 5C ML Inference FastAPI application.

Tests:
1. Health endpoint (GET /api/v1/health) - 200 OK when model loaded
2. Health endpoint 503 simulation when model not loaded
3. Authentication on POST /api/v1/predict:
   - Missing X-API-Key returns 401 MISSING_API_KEY
   - Invalid X-API-Key returns 403 INVALID_API_KEY
   - Valid X-API-Key succeeds
4. Input validation and error handling:
   - Invalid JSON body returns 400 INVALID_JSON
   - Missing features object returns 400 MISSING_FEATURES_OBJECT
   - Missing required features returns 422 MISSING_REQUIRED_FEATURES
   - Target leakage field returns 422 LEAKAGE_FIELD_DETECTED
   - Invalid feature type returns 422 INVALID_FEATURE_TYPE
5. Prediction output correctness:
   - Valid payload returns 200 OK with full contract structure
   - Model provenance and SHA-256 match pinned metadata
   - Event ID is echoed accurately (and handled when null)
   - Probabilities sum to 1.0 and confidence aligns with thresholds
"""

import os
from typing import Any, Dict
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import (
    API_KEY,
    DEFAULT_API_KEY,
    EXPECTED_MODEL_SHA256,
    MODEL_ARCHITECTURE,
    MODEL_MACRO_F1_OOF,
    MODEL_TRAINING_SAMPLES,
    MODEL_VERSION_IDENTIFIER,
    app,
    app_state,
)
from src.models.predict import (
    CONFIDENCE_TIERS,
    PRODUCTION_CLASSES,
    REQUIRED_FEATURES,
    TARGET_LEAKAGE_FIELDS,
)


@pytest.fixture(scope="module")
def valid_features() -> Dict[str, Any]:
    """Provide a valid 36-feature dictionary from the vetted dataset."""
    dataset_path = os.path.join("outputs", "phase_4c_ml", "ml_3class_dataset.csv")
    assert os.path.exists(dataset_path), f"Dataset missing at {dataset_path}"
    df = pd.read_csv(dataset_path)
    record = df.iloc[0].to_dict()
    return {k: record[k] for k in REQUIRED_FEATURES}


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient context fixture."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------


def test_health_check_success(client):
    """GET /api/v1/health returns 200 OK and model metadata when loaded."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["model_version"] == MODEL_VERSION_IDENTIFIER
    assert data["model_sha256"] == EXPECTED_MODEL_SHA256
    assert data["required_features_count"] == 36
    assert set(data["production_classes"]) == set(PRODUCTION_CLASSES)
    assert data["api_version"] == "1.0.0"
    assert "timestamp" in data


def test_health_check_unavailable_simulation(client):
    """GET /api/v1/health returns 503 when model_loaded is False."""
    original_state = app_state["model_loaded"]
    original_error = app_state["model_error"]

    try:
        app_state["model_loaded"] = False
        app_state["model_error"] = "Simulated model outage"

        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["model_loaded"] is False
        assert "error" in data
    finally:
        app_state["model_loaded"] = original_state
        app_state["model_error"] = original_error


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


def test_predict_missing_api_key(client, valid_features):
    """POST /api/v1/predict without X-API-Key header returns 401 MISSING_API_KEY."""
    response = client.post(
        "/api/v1/predict",
        json={"event_id": "TEST_AUTH", "features": valid_features},
    )
    assert response.status_code == 401
    err = response.json().get("error", {})
    assert err.get("code") == "MISSING_API_KEY"
    assert "Missing required X-API-Key" in err.get("message", "")


def test_predict_invalid_api_key(client, valid_features):
    """POST /api/v1/predict with wrong X-API-Key returns 403 INVALID_API_KEY."""
    response = client.post(
        "/api/v1/predict",
        json={"event_id": "TEST_AUTH", "features": valid_features},
        headers={"X-API-Key": "incorrect-api-key-1234"},
    )
    assert response.status_code == 403
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_API_KEY"
    assert "Invalid API key" in err.get("message", "")


# ---------------------------------------------------------------------------
# Input Validation & Error Envelope Tests
# ---------------------------------------------------------------------------


def test_predict_invalid_json(client):
    """POST /api/v1/predict with non-JSON body returns 400 INVALID_JSON."""
    response = client.post(
        "/api/v1/predict",
        content="not a valid json payload",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_JSON"
    assert "Request body is not valid JSON" in err.get("message", "")


def test_predict_missing_features_object(client):
    """POST /api/v1/predict missing 'features' returns 400 MISSING_FEATURES_OBJECT."""
    response = client.post(
        "/api/v1/predict",
        json={"event_id": "TEST_MISSING_OBJ"},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "MISSING_FEATURES_OBJECT"
    assert "must contain a 'features' object" in err.get("message", "")


def test_predict_missing_required_features(client, valid_features):
    """POST /api/v1/predict with missing required fields returns 422 MISSING_REQUIRED_FEATURES."""
    incomplete = valid_features.copy()
    del incomplete["frp"]
    del incomplete["distance_to_facility_m"]

    response = client.post(
        "/api/v1/predict",
        json={"event_id": "TEST_INC", "features": incomplete},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "MISSING_REQUIRED_FEATURES"
    assert "Missing 2 required feature(s)" in err.get("message", "")
    assert "frp" in err.get("details", {}).get("missing", [])
    assert "distance_to_facility_m" in err.get("details", {}).get("missing", [])


def test_predict_target_leakage_blocked(client, valid_features):
    """POST /api/v1/predict with ground truth fields returns 422 LEAKAGE_FIELD_DETECTED."""
    leaky = valid_features.copy()
    leaky["human_ground_truth_class"] = "Industrial Thermal Activity"

    response = client.post(
        "/api/v1/predict",
        json={"event_id": "TEST_LEAK", "features": leaky},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "LEAKAGE_FIELD_DETECTED"
    assert "human_ground_truth_class" in err.get("details", {}).get(
        "leakage_fields_detected", []
    )


def test_predict_invalid_feature_type(client, valid_features):
    """POST /api/v1/predict with uncoercible types returns 422 INVALID_FEATURE_TYPE."""
    invalid_payload = valid_features.copy()
    invalid_payload["frp"] = "uncoercible_string"

    response = client.post(
        "/api/v1/predict",
        json={"event_id": "TEST_TYPE", "features": invalid_payload},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_FEATURE_TYPE"
    assert "frp" in err.get("details", {}).get("invalid_fields", [])


# ---------------------------------------------------------------------------
# Successful Prediction Tests
# ---------------------------------------------------------------------------


def test_predict_success_with_event_id(client, valid_features):
    """POST /api/v1/predict returns contract-compliant 200 OK response with event_id."""
    event_id = "FIRMS_TN_SAMPLE_001"
    response = client.post(
        "/api/v1/predict",
        json={"event_id": event_id, "features": valid_features},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 200
    data = response.json()

    # Echoed event_id
    assert data["event_id"] == event_id

    # Predicted class
    assert data["predicted_class"] in PRODUCTION_CLASSES

    # Probabilities
    probs = data["probabilities"]
    assert set(probs.keys()) == set(PRODUCTION_CLASSES)
    for p in probs.values():
        assert 0.0 <= p <= 1.0
    assert pytest.approx(sum(probs.values()), abs=1e-3) == 1.0

    # Max probability & confidence
    assert data["max_probability"] == max(probs.values())
    assert data["ml_confidence"] in CONFIDENCE_TIERS

    # Confidence scale
    assert "HIGH" in data["confidence_scale"]
    assert "MEDIUM" in data["confidence_scale"]
    assert "LOW" in data["confidence_scale"]

    # Model provenance
    model_info = data["model"]
    assert model_info["version"] == MODEL_VERSION_IDENTIFIER
    assert model_info["sha256"] == EXPECTED_MODEL_SHA256
    assert model_info["architecture"] == MODEL_ARCHITECTURE
    assert model_info["training_samples"] == MODEL_TRAINING_SAMPLES
    assert model_info["macro_f1_oof"] == MODEL_MACRO_F1_OOF

    # Metadata & disclaimer
    assert "inference_timestamp" in data
    assert "disclaimer" in data
    assert "Prediction is an algorithmic ML estimate" in data["disclaimer"]


def test_predict_success_without_event_id(client, valid_features):
    """POST /api/v1/predict supports optional event_id (returns null)."""
    response = client.post(
        "/api/v1/predict",
        json={"features": valid_features},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] is None
    assert data["predicted_class"] in PRODUCTION_CLASSES
