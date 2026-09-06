# ML API CONTRACT
## Industrial Fire Detection — Backend Inference API

**Status:** Design only — no implementation exists yet.
**Inspection basis:** `src/models/predict.py`, `tests/test_ml_inference.py`,
`outputs/phase_5_ml_handoff/final_model_metadata.json`,
`outputs/phase_5_ml_handoff/model_manifest.json`,
`outputs/phase_5_ml_handoff/ML_INFERENCE_README.md`,
`outputs/phase_5_ml_handoff/feature_manifest_baseline.csv`
**Date:** 2026-09-06

---

## PART A — EXISTING INFERENCE INTERFACE INSPECTION

### A1. Available Functions

| Function | Signature | Behaviour | Returns |
|----------|-----------|-----------|---------|
| `load_production_model` | `(model_path=None) -> Pipeline` | Loads joblib from disk; caches in module-level `_CACHED_MODEL`. Tries primary path then fallback `phase_5_ml_handoff`. | `sklearn.pipeline.Pipeline` |
| `get_required_features` | `() -> List[str]` | Returns ordered list of 36 feature names. | `List[str]` |
| `validate_and_prepare_features` | `(features) -> DataFrame` | Checks for leakage fields; checks all 36 features present; returns 36-column DataFrame in canonical order. | `pd.DataFrame` |
| `determine_confidence_category` | `(max_probability: float) -> str` | >= 0.75 -> HIGH, 0.50-0.74 -> MEDIUM, < 0.50 -> LOW. | `str` |
| **`predict_event`** | `(features, model_path=None) -> Dict` | Single-event interface. Validates, loads model, returns full result dict. Enforces exactly 1 row. | `Dict[str, Any]` |
| **`predict_batch`** | `(events_df: DataFrame, model_path=None) -> List[Dict]` | Batch interface. Processes N rows. Returns abbreviated per-event dicts. | `List[Dict[str, Any]]` |

#### `predict_event` full return structure:
```python
{
    "prediction":       str,    # one of 3 production classes
    "probabilities": {          # class -> float, sum = 1.0 +/- 1e-4
        "Agricultural Burning":         float,
        "Industrial Thermal Activity":  float,
        "Natural / Wildfire / Other":   float,
    },
    "max_probability":    float,  # highest class probability, 4dp
    "confidence":         str,    # "HIGH" | "MEDIUM" | "LOW"
    "confidence_scale": {         # threshold definitions
        "HIGH":   ">= 0.75",
        "MEDIUM": "0.50 - 0.74",
        "LOW":    "< 0.50",
    },
    "model_architecture": str,    # "Random Forest Classifier ..."
    "note":               str,    # disclaimer string
}
```

#### `predict_batch` per-element structure (abbreviated):
```python
{
    "prediction":      str,
    "probabilities":   { ... },
    "max_probability": float,
    "confidence":      str,
}
```

**Key difference:** `predict_batch` omits `confidence_scale`, `model_architecture`, and `note`.
The API response will normalise both interfaces to a single consistent schema.

---

### A2. Required Model Inputs — 36 Baseline Features

All 36 features are REQUIRED — none are optional.
The model pipeline handles internal imputation (numeric) and one-hot encoding (categorical).

#### Sub-group 1 — NASA FIRMS Thermal Intensity (8, all numeric)

| # | Feature | Type | Notes |
|---|---------|------|-------|
| 1 | `frp` | float | Fire Radiative Power (MW) |
| 2 | `brightness` | float | I4 brightness temperature (K) |
| 3 | `bright_t31` | float | I5 brightness temperature (K) |
| 4 | `brightness_difference` | float | I4 - I5 (K) |
| 5 | `frp_brightness_ratio` | float | FRP / brightness |
| 6 | `log_frp` | float | log1p(frp) |
| 7 | `confidence_numeric` | int 1/2 | 1=nominal, 2=high |
| 8 | `is_day` | int 0/1 | 1=daytime |

#### Sub-group 2 — NASA FIRMS Persistence & Anomaly (10, numeric/binary)

| # | Feature | Type | Notes |
|---|---------|------|-------|
| 9 | `grid_detection_count` | int | Total detections in 0.05 deg cell |
| 10 | `grid_active_days` | int | Distinct active days |
| 11 | `persistent_location_flag` | int 0/1 | grid_active_days >= 3 |
| 12 | `grid_total_frp` | float | Cumulative FRP in cell |
| 13 | `grid_brightness_mean` | float | Mean brightness across cell |
| 14 | `high_brightness_flag_local` | int 0/1 | Local brightness spike |
| 15 | `high_frp_flag_local` | int 0/1 | Local FRP spike |
| 16 | `brightness_zscore_local` | float | Standardised brightness z-score |
| 17 | `frp_zscore_local` | float | Standardised FRP z-score |
| 18 | `is_stubble_burning_season` | int 0/1 | Seasonal flag |

#### Sub-group 3 — ESA WorldCover (1, categorical -> one-hot)

| # | Feature | Type | Notes |
|---|---------|------|-------|
| 19 | `landcover_code` | int | 10=Tree, 20=Shrub, 30=Grass, 40=Crop, 50=Built-up, 60=Bare |

#### Sub-group 4 — OpenStreetMap Proximity & Context (17, numeric + 4 categorical)

| # | Feature | Type | Notes |
|---|---------|------|-------|
| 20 | `distance_to_facility_m` | float | Metres to nearest facility |
| 21 | `nearest_facility_type` | str | CATEGORICAL -> one-hot |
| 22 | `nearest_facility_category` | str | CATEGORICAL -> one-hot |
| 23 | `nearest_facility_tier` | str | CATEGORICAL -> one-hot (HIGHER_RELEVANCE / CAUTION_LOWER_RELEVANCE / GENERAL_CONTEXT) |
| 24 | `near_industrial_500m` | int 0/1 | |
| 25 | `near_industrial_1000m` | int 0/1 | |
| 26 | `near_industrial_2000m` | int 0/1 | |
| 27 | `near_industrial_5000m` | int 0/1 | |
| 28 | `near_industrial_10000m` | int 0/1 | |
| 29 | `distance_to_higher_relevance_m` | float | Metres to nearest high-relevance facility |
| 30 | `nearest_hr_category` | str | CATEGORICAL -> one-hot |
| 31 | `near_higher_relevance_500m` | int 0/1 | |
| 32 | `near_higher_relevance_1000m` | int 0/1 | |
| 33 | `near_higher_relevance_2000m` | int 0/1 | |
| 34 | `near_higher_relevance_5000m` | int 0/1 | |
| 35 | `near_higher_relevance_10000m` | int 0/1 | |
| 36 | `osm_coverage_status` | str | CATEGORICAL -> one-hot (COVERED / FAILED_TILE) |

> **Sentinel-2 not required.** `model_manifest.json` flag `requires_sentinel2_at_inference = false`.
> The API must NEVER request spectral raster data from the frontend.

---

### A3. Model Outputs

| Field | Type | Description |
|-------|------|-------------|
| `prediction` | str | Winning class name |
| `probabilities["Agricultural Burning"]` | float [0,1] | Class probability |
| `probabilities["Industrial Thermal Activity"]` | float [0,1] | Class probability |
| `probabilities["Natural / Wildfire / Other"]` | float [0,1] | Class probability |
| `max_probability` | float [0,1] | Max of the three probabilities (4dp) |
| `confidence` | str | HIGH / MEDIUM / LOW |

**Probability ordering in model internals** (from `model_manifest.json`, `class_ordering_in_probabilities`):
1. Agricultural Burning
2. Industrial Thermal Activity
3. Natural / Wildfire / Other

Probabilities sum to 1.0 +/- 1e-4.

---

### A4. Error Handling

| Error Condition | Exception Type | Message Pattern |
|-----------------|---------------|-----------------|
| Missing required feature(s) | `ValueError` | "Missing N required feature(s) for production model: ['frp', ...]" |
| Target leakage field present | `ValueError` | "Target leakage detected! The following ground-truth/heuristic fields must NOT be passed: [...]" |
| Wrong input type | `TypeError` | "Input features must be a dict, pd.Series, or pd.DataFrame, got: <class '...'>" |
| Model file not found | `FileNotFoundError` | "Production model artifact not found at: <path> (or fallback: <path>)" |
| Loaded object not a Pipeline | `TypeError` | "Expected scikit-learn Pipeline object, got: <type>" |
| predict_event given >1 row | `ValueError` | "predict_event expects exactly 1 event record, received N rows." |

**Target leakage fields (hardcoded in predict.py):**
`ml_target_3class`, `human_ground_truth_class`, `human_raw_label`, `weak_label`,
`ground_truth_status`, `human_validation_status`, `human_industry_observation`,
`human_review_confidence`, `is_unambiguous_ground_truth`

---

### A5. Existing Tests (`tests/test_ml_inference.py`)

| Test | Coverage |
|------|----------|
| `test_model_loading` | Loads, has predict/predict_proba/classes_, exactly 3 classes |
| `test_predict_event_valid_output` | Output structure; class in PRODUCTION_CLASSES; probs in [0,1]; sum ~= 1.0; max_probability correct; confidence in CONFIDENCE_TIERS; tier aligns with thresholds |
| `test_missing_feature_raises_error` | ValueError raised; feature names in message |
| `test_target_leakage_fields_raise_error` | ValueError for each leakage field; "Target leakage detected" in message |
| `test_batch_prediction` | 5-row batch; list of 5 dicts; each has prediction, confidence, 3 probabilities |
| `test_reproducibility` | Same input -> identical output on two consecutive calls |

**Behaviours NOT yet tested (gaps for Step 2):**
- Invalid model path (FileNotFoundError)
- Wrong data type input (TypeError)
- predict_event with >1 row DataFrame
- API HTTP layer validation (JSON parsing, field types, value ranges)
- HTTP error response schemas (400, 422, 401, 503)
- Concurrent request handling / model thread safety
- Startup cold-start model loading
- SHA-256 hash verification at startup

---

## PART B — PROPOSED API CONTRACT

### B1. API Overview

| Property | Value |
|----------|-------|
| Protocol | HTTP/1.1 or HTTP/2 |
| Format | JSON (Content-Type: application/json) |
| Encoding | UTF-8 |
| Authentication | API key via `X-API-Key` header |
| Versioning | URL prefix `/api/v1/` |
| Inference backend | `src.models.predict.predict_event()` |
| Model file | `outputs/phase_5_ml_handoff/final_model.joblib` |
| Sentinel-2 required | NO |
| Model modified by API | NEVER |
| Base URL (development) | `http://localhost:8000/api/v1` |

---

### B2. POST /api/v1/predict

Runs 3-class ML inference for a single thermal event.

#### Request Headers

| Header | Required | Value |
|--------|----------|-------|
| `Content-Type` | Yes | `application/json` |
| `X-API-Key` | Yes | Bearer API key |

#### Request Body

```json
{
  "event_id": "FIRMS_TN_0012",
  "features": {
    "frp": 2.09,
    "brightness": 325.4,
    "...": "...(all 36 features)..."
  }
}
```

| Top-level Field | Type | Required | Description |
|----------------|------|----------|-------------|
| `event_id` | string | Optional | Caller-supplied identifier. Echoed in response. No validation. |
| `features` | object | REQUIRED | Exactly the 36 baseline ML features. |

**Fields that MUST NOT be sent (API returns 422 if present):**
`human_ground_truth_class`, `ml_target_3class`, `weak_label`, `ground_truth_status`,
`human_validation_status`, `human_raw_label`, `human_review_confidence`,
`is_unambiguous_ground_truth`, `human_industry_observation`

---

#### Response — 200 OK

```json
{
  "event_id": "FIRMS_TN_0012",
  "predicted_class": "Industrial Thermal Activity",
  "probabilities": {
    "Agricultural Burning": 0.0513,
    "Industrial Thermal Activity": 0.9184,
    "Natural / Wildfire / Other": 0.0303
  },
  "max_probability": 0.9184,
  "ml_confidence": "HIGH",
  "confidence_scale": {
    "HIGH":   ">= 0.75",
    "MEDIUM": "0.50 - 0.74",
    "LOW":    "< 0.50"
  },
  "model": {
    "version":          "phase_5_ml_handoff/final_model.joblib",
    "sha256":           "5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798",
    "architecture":     "Random Forest Classifier (Baseline FIRMS+OSM+WorldCover)",
    "training_samples": 76,
    "macro_f1_oof":     0.7772
  },
  "inference_timestamp": "2026-09-06T17:47:00Z",
  "disclaimer": "Prediction is an algorithmic ML estimate. It is not ground truth."
}
```

| Response Field | Type | Description |
|---------------|------|-------------|
| `event_id` | string / null | Echo of caller-supplied event_id, or null |
| `predicted_class` | string | "Agricultural Burning" / "Industrial Thermal Activity" / "Natural / Wildfire / Other" |
| `probabilities` | object | All 3 class probabilities, float [0,1], sum ~= 1.0 |
| `max_probability` | float | Highest class probability (4dp) |
| `ml_confidence` | string | "HIGH" / "MEDIUM" / "LOW" |
| `confidence_scale` | object | Tier threshold definitions |
| `model.version` | string | Model artifact identifier |
| `model.sha256` | string | SHA-256 of model file |
| `model.architecture` | string | Model type description |
| `model.training_samples` | int | 76 |
| `model.macro_f1_oof` | float | 0.7772 |
| `inference_timestamp` | string | ISO 8601 UTC |
| `disclaimer` | string | Fixed disclaimer |

---

### B3. GET /api/v1/health

Liveness and model readiness check. No authentication required.

#### Response — 200 OK (model ready)

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "phase_5_ml_handoff/final_model.joblib",
  "model_sha256": "5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798",
  "required_features_count": 36,
  "production_classes": [
    "Agricultural Burning",
    "Industrial Thermal Activity",
    "Natural / Wildfire / Other"
  ],
  "api_version": "1.0.0",
  "timestamp": "2026-09-06T17:47:00Z"
}
```

#### Response — 503 Service Unavailable (model not loaded)

```json
{
  "status": "unavailable",
  "model_loaded": false,
  "error": "Model artifact not found at expected path.",
  "timestamp": "2026-09-06T17:47:00Z"
}
```

---

### B4. Error Responses

All errors use a consistent envelope:

```json
{
  "error": {
    "code": "<ERROR_CODE>",
    "message": "<human-readable description>",
    "details": {}
  }
}
```

| HTTP Status | Error Code | Trigger |
|-------------|-----------|---------|
| 400 | `INVALID_JSON` | Request body is not valid JSON |
| 400 | `MISSING_FEATURES_OBJECT` | `features` key absent |
| 422 | `MISSING_REQUIRED_FEATURES` | One or more of the 36 features absent |
| 422 | `LEAKAGE_FIELD_DETECTED` | Ground-truth field detected in features |
| 422 | `INVALID_FEATURE_TYPE` | Feature value cannot be coerced to expected type |
| 401 | `MISSING_API_KEY` | `X-API-Key` header absent |
| 403 | `INVALID_API_KEY` | Key present but not valid |
| 429 | `RATE_LIMIT_EXCEEDED` | Rate limit hit |
| 500 | `INFERENCE_ERROR` | Unexpected model error |
| 503 | `MODEL_NOT_LOADED` | Model failed to load at startup |

**Example 422 — missing features:**
```json
{
  "error": {
    "code": "MISSING_REQUIRED_FEATURES",
    "message": "Missing 2 required feature(s) for production model.",
    "details": {
      "missing": ["frp", "distance_to_facility_m"],
      "total_required": 36,
      "total_provided": 34
    }
  }
}
```

**Example 422 — leakage field:**
```json
{
  "error": {
    "code": "LEAKAGE_FIELD_DETECTED",
    "message": "Ground-truth fields must not be passed as inference features.",
    "details": {
      "leakage_fields_detected": ["human_ground_truth_class"]
    }
  }
}
```

---

### B5. Full Example Request/Response

**Request:**
```http
POST /api/v1/predict HTTP/1.1
Content-Type: application/json
X-API-Key: <api_key>

{
  "event_id": "FIRMS_TN_0012",
  "features": {
    "frp": 2.09,
    "brightness": 325.4,
    "bright_t31": 298.1,
    "brightness_difference": 27.3,
    "frp_brightness_ratio": 0.0064,
    "log_frp": 1.128,
    "confidence_numeric": 2,
    "is_day": 1,
    "grid_detection_count": 12,
    "grid_active_days": 8,
    "persistent_location_flag": 1,
    "grid_total_frp": 38.5,
    "grid_brightness_mean": 320.1,
    "high_brightness_flag_local": 0,
    "high_frp_flag_local": 0,
    "brightness_zscore_local": 0.42,
    "frp_zscore_local": -0.15,
    "is_stubble_burning_season": 0,
    "landcover_code": 50,
    "distance_to_facility_m": 120.5,
    "nearest_facility_type": "industrial",
    "nearest_facility_category": "Steel / Metallurgy",
    "nearest_facility_tier": "HIGHER_RELEVANCE",
    "near_industrial_500m": 1,
    "near_industrial_1000m": 1,
    "near_industrial_2000m": 1,
    "near_industrial_5000m": 1,
    "near_industrial_10000m": 1,
    "distance_to_higher_relevance_m": 120.5,
    "nearest_hr_category": "Steel / Metallurgy",
    "near_higher_relevance_500m": 1,
    "near_higher_relevance_1000m": 1,
    "near_higher_relevance_2000m": 1,
    "near_higher_relevance_5000m": 1,
    "near_higher_relevance_10000m": 1,
    "osm_coverage_status": "COVERED"
  }
}
```

**Response (200 OK):**
```json
{
  "event_id": "FIRMS_TN_0012",
  "predicted_class": "Industrial Thermal Activity",
  "probabilities": {
    "Agricultural Burning": 0.0513,
    "Industrial Thermal Activity": 0.9184,
    "Natural / Wildfire / Other": 0.0303
  },
  "max_probability": 0.9184,
  "ml_confidence": "HIGH",
  "confidence_scale": {
    "HIGH": ">= 0.75",
    "MEDIUM": "0.50 - 0.74",
    "LOW": "< 0.50"
  },
  "model": {
    "version": "phase_5_ml_handoff/final_model.joblib",
    "sha256": "5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798",
    "architecture": "Random Forest Classifier (Baseline FIRMS+OSM+WorldCover)",
    "training_samples": 76,
    "macro_f1_oof": 0.7772
  },
  "inference_timestamp": "2026-09-06T17:47:00Z",
  "disclaimer": "Prediction is an algorithmic ML estimate. It is not ground truth."
}
```

---

### B6. Model Provenance

| Property | Value |
|----------|-------|
| Model type | RandomForestClassifier |
| Pipeline | ColumnTransformer (imputation + one-hot) -> RandomForestClassifier |
| n_estimators | 100 |
| max_depth | 6 |
| class_weight | balanced |
| random_state | 42 |
| Training samples | 76 |
| Macro F1 OOF | 0.7772 |
| Macro F1 CV mean | 0.7594 +/- 0.1173 |
| Industrial Thermal Recall | 93.3% |
| Agricultural Burning Recall | 90.0% |
| Natural/Other Recall | 54.5% (11 training samples only) |
| Model SHA-256 | 5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798 |
| File size | 236,067 bytes |
| Training timestamp | 2026-09-06T08:26:00Z |

---

### B7. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Authentication | X-API-Key header required for POST /predict. Validated server-side from env var — never in code. |
| Model exposure | final_model.joblib is never served. Only predictions returned. |
| Leakage field injection | validate_and_prepare_features() raises ValueError on any leakage field — enforced at Python layer, not just API layer. |
| Input validation | API validates JSON schema and feature types before calling predict_event(). |
| Rate limiting | 100 req/min per key recommended. |
| HTTPS | All production traffic must use TLS. HTTP redirects to HTTPS. |
| CORS | Restrict Allow-Origin to known frontend domains in production. |
| Error information leakage | Missing feature names exposed for debugging; model internals, training data, and filesystem paths never exposed. |
| Model tampering | SHA-256 verified at startup against pinned expected value. Server refuses to start on mismatch. |
| Credential logging | X-API-Key values must never appear in server logs. |

---

### B8. Frontend Integration Notes

1. **Do not send Sentinel-2 data.** All 36 features come from FIRMS, OSM, and WorldCover.

2. **Use event_id for correlation.** Pass the event_id from dashboard_events_633.csv for response matching.

3. **Display ml_confidence with colour coding.** HIGH=green, MEDIUM=amber, LOW=red.

4. **Show probability bars for all 3 classes.** Never show only the winning class.

5. **Label predictions clearly as ML estimates.** Use "ML Prediction" — not "Classification" or "Ground Truth".

6. **Poll GET /health before displaying the predict UI.** If model_loaded=false, show a maintenance notice.

7. **Derived features must be computed before calling the API.** The following cannot be read directly from raw FIRMS:
   frp_brightness_ratio, log_frp, brightness_difference,
   brightness_zscore_local, frp_zscore_local, grid_*, is_stubble_burning_season.
   A data pipeline must compute these for new live events.

8. **Handle LOW confidence gracefully.** 11.5% of 633 events were LOW — show "Manual review recommended".

9. **Natural / Wildfire / Other has lowest recall (54.5%).** Consider a caution badge for this class.

10. **For pre-built 633-event data** use dashboard_events_633.csv directly. The API is for new/live events only.

---

### B9. Recommended Implementation Stack

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| Framework | FastAPI | Native async, auto OpenAPI docs, Pydantic validation |
| ASGI server | Uvicorn | Production-grade, pairs with FastAPI |
| Model loading | At startup (lifespan event) | Avoids cold-start on first request |
| Request validation | Pydantic BaseModel | Type coercion + automatic 422 generation |
| Logging | Python logging -> structured JSON | Consistent with ThermalAnomalyInference logger |
| Tests | pytest + httpx | Extends existing tests/test_ml_inference.py |

---

## SUMMARY

| Item | Status |
|------|--------|
| predict_event() interface inspected | DONE |
| predict_batch() interface inspected | DONE |
| 36 required features documented | DONE |
| Model outputs documented | DONE |
| Error handling documented | DONE |
| Existing test coverage catalogued | DONE |
| Test gaps identified | DONE |
| POST /predict contract designed | DONE |
| GET /health contract designed | DONE |
| API implemented | NOT YET (Phase 5C Step 2) |

---

*Design only. No files modified. No API implemented. No Git operations performed.*
