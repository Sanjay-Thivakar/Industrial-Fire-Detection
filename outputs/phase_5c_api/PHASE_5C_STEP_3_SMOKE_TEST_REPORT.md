# PHASE 5C — STEP 3: BACKEND SMOKE TEST & PRODUCTION VERIFICATION REPORT
## Industrial Fire Detection — Backend ML Inference API

**Date:** 2026-09-06  
**Execution Type:** Local Live Smoke Test & End-to-End Production Verification  
**Target Classifiers:** 3-Class Baseline Random Forest (Agricultural Burning, Industrial Thermal Activity, Natural / Wildfire / Other)  
**Overall Result:** **PASS** (11/11 Verification Steps Succeeded; 138/138 Pytest Suite Passed)  

---

## 1. Test Environment

| Parameter | Specification |
|---|---|
| **Operating System** | Windows 11 (win32) |
| **Python Runtime** | Python 3.11.6 |
| **Web Framework** | FastAPI 0.115.x / Starlette |
| **ASGI Server** | Uvicorn 0.34.x (Standard worker) |
| **Validation Engine** | Pydantic 2.10.x |
| **HTTP Test Client** | HTTPX 0.28.x |
| **Machine Learning Stack** | scikit-learn 1.4+, joblib 1.4+, numpy, pandas |
| **Network Binding** | `127.0.0.1:8008` (Strict localhost loopback; non-public) |
| **Authentication Source** | Environment variable (`ML_API_KEY`) |

---

## 2. API Startup Result

The FastAPI inference application (`src/api/main.py`) was started via an isolated local Uvicorn process bound strictly to `127.0.0.1:8008`:

- **Lifespan Startup:** Triggered automatically upon server boot.
- **Model Loading:** Production model pre-loaded into memory from `outputs/phase_5_ml_handoff/final_model.joblib`.
- **Integrity Validation:** SHA-256 calculated dynamically at boot and verified against the production manifest.
- **Boot Time:** Server successfully initialized and reported healthy within 2.5 seconds.
- **Log Sanitation:** Zero credentials or sensitive environment secrets emitted during initialization.

---

## 3. Health Endpoint Result

**Request:** `GET http://127.0.0.1:8008/api/v1/health` (No authentication required)  
**HTTP Status:** `200 OK`  

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
  "timestamp": "2026-09-06T18:18:49Z"
}
```

- Liveness check: **PASS**
- Model loaded confirmation: **PASS**
- Reported SHA-256 match: **PASS** (`5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798`)
- Required feature count (36): **PASS**
- Production class list (3 classes): **PASS**

---

## 4. Real-Event Prediction Result

**Dataset Source:** Authoritative 633-event master dataset (`outputs/phase_4b_ground_truth/sentinel2_master_633_human_ground_truth.csv`)  
**Event Selected:** `FIRMS_TN_0000` (VIIRS detection near Salem Steel Plant / SAIL)  
**Input Payload:** 36 canonical features extracted directly from source event record; ground-truth / leakage columns omitted.  
**Request:** `POST http://127.0.0.1:8008/api/v1/predict` with `X-API-Key` supplied from environment.  
**HTTP Status:** `200 OK`  

```json
{
  "event_id": "FIRMS_TN_0000",
  "predicted_class": "Industrial Thermal Activity",
  "probabilities": {
    "Agricultural Burning": 0.4331,
    "Industrial Thermal Activity": 0.5031,
    "Natural / Wildfire / Other": 0.0639
  },
  "max_probability": 0.5031,
  "ml_confidence": "MEDIUM",
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
  "inference_timestamp": "2026-09-06T18:18:49Z",
  "disclaimer": "Prediction is an algorithmic ML estimate. It is not ground truth."
}
```

- Event ID preserved: **PASS** (`FIRMS_TN_0000`)
- Predicted class valid: **PASS** (`Industrial Thermal Activity`)
- All 3 class probabilities returned: **PASS**
- Probabilities sum: **PASS** (0.4331 + 0.5031 + 0.0639 = 1.0001 ~= 1.0)
- Max probability: **PASS** (`0.5031`)
- Confidence tier: **PASS** (`MEDIUM`, aligns with 0.50 <= p < 0.75)
- Model provenance block: **PASS**
- Timestamp present: **PASS**
- Disclaimer present: **PASS**

---

## 5. Direct `predict.py` Comparison

To verify zero drift between the API layer and the underlying machine learning backend, `src/models/predict.py:predict_event()` was called independently in Python using the exact same feature vector for `FIRMS_TN_0000`.

| Metric / Field | API Endpoint Output | Direct `predict.py` Output | Match Status |
|---|---|---|---|
| **Predicted Class** | `Industrial Thermal Activity` | `Industrial Thermal Activity` | **EXACT MATCH** |
| **Probability (Industrial)** | `0.5031` | `0.5031` | **EXACT MATCH** |
| **Probability (Agricultural)** | `0.4331` | `0.4331` | **EXACT MATCH** |
| **Probability (Natural/Other)**| `0.0639` | `0.0639` | **EXACT MATCH** |
| **Max Probability** | `0.5031` | `0.5031` | **EXACT MATCH** |
| **Confidence Tier** | `MEDIUM` | `MEDIUM` | **EXACT MATCH** |
| **Phase 5A Batch Record** | `Industrial Thermal Activity` (0.5031) | `Industrial Thermal Activity` (0.5031) | **EXACT MATCH** |

**Conclusion:** 100% numerical and categorical equivalence across the API, Python inference engine, and Phase 5A historical prediction batch.

---

## 6. Authentication Tests

The API authentication mechanism on `POST /api/v1/predict` was verified against three conditions:

| Scenario | Request Header | Expected Status | Actual Status | Error Code | Message | Result |
|---|---|---|---|---|---|---|
| **Omitted Key** | None | 401 | 401 | `MISSING_API_KEY` | "Missing required X-API-Key header." | **PASS** |
| **Invalid Key** | `X-API-Key: [REDACTED_INVALID]` | 403 | 403 | `INVALID_API_KEY` | "Invalid API key provided." | **PASS** |
| **Valid Key** | `X-API-Key: [REDACTED_VALID]` | 200 | 200 | N/A | Successful prediction | **PASS** |

- Unauthenticated and unauthorized requests are blocked before reaching model inference.
- API keys are never echoed back in response headers or response payloads.

---

## 7. Negative Request Tests

Validation enforcement and contract-compliant error envelopes were tested against five negative input conditions:

| Negative Scenario | Trigger | Status | Error Code | Detail Summary | Envelope Compliance |
|---|---|---|---|---|---|
| **Missing Features Object** | Body missing `features` key (`{"event_id": "NEG1"}`) | 400 | `MISSING_FEATURES_OBJECT` | "Request body must contain a 'features' object." | **PASS** |
| **Missing Required Feature** | Feature `frp` removed (35/36 provided) | 422 | `MISSING_REQUIRED_FEATURES` | `details.missing: ["frp"]`, required: 36, provided: 35 | **PASS** |
| **Target Leakage Field** | Ground truth field `human_ground_truth_class` injected | 422 | `LEAKAGE_FIELD_DETECTED` | `details.leakage_fields_detected: ["human_ground_truth_class"]` | **PASS** |
| **Invalid Feature Type** | String `"not_a_valid_number"` supplied for `frp` | 422 | `INVALID_FEATURE_TYPE` | `details.invalid_fields: ["frp"]` | **PASS** |
| **Malformed JSON** | Non-JSON text payload sent with JSON header | 400 | `INVALID_JSON` | "Request body is not valid JSON." | **PASS** |

All negative responses strictly conformed to the standard error contract:
```json
{
  "error": {
    "code": "<CODE>",
    "message": "<MESSAGE>",
    "details": {}
  }
}
```

---

## 8. Security Verification

- **API Key Storage:** The API key is resolved from `os.environ.get("ML_API_KEY")`; no secrets or keys are hardcoded in application logic.
- **Response Sanitization:** Verified that no API key, authorization token, or credential was reflected in any client response.
- **Log Leakage Audit:** Inspection of Uvicorn stdout and stderr verified zero logging of headers, keys, or authorization tokens.
- **Filesystem Privacy:** No internal directory paths (e.g., local user directories or drive letters) were exposed in HTTP responses.
- **Exception Shielding:** No raw Python tracebacks were surfaced to clients; all exceptions were intercepted and converted to structured JSON.
- **Non-Public Interface:** Server was bound strictly to `127.0.0.1` (localhost).

---

## 9. Production Model SHA-256 Verification

Both canonical copies of the production model artifact were verified via direct SHA-256 digest computation:

| Model Path | File Size | Computed SHA-256 Digest | Expected Digest | Match Status |
|---|---|---|---|---|
| `outputs/phase_4d_models/final_model.joblib` | 236,067 bytes | `5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798` | `5909bb54...` | **MATCH** |
| `outputs/phase_5_ml_handoff/final_model.joblib` | 236,067 bytes | `5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798` | `5909bb54...` | **MATCH** |

Both files remain byte-for-byte identical, unmodified, and uncorrupted.

---

## 10. Complete Pytest Result

The entire project automated test suite was executed via `pytest -v`:

```
============================= test session starts =============================
platform win32 -- Python 3.11.6, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\divas\Desktop\Industrial-Fire-Detection
collected 138 items

tests/test_api.py (11 tests) ............................................ PASSED
tests/test_cdse_auth_minimal.py (1 test) ................................ PASSED
tests/test_cdse_live_smoke.py (1 test) .................................. PASSED
tests/test_feature_engineering.py (8 tests) ............................. PASSED
tests/test_firms_loader.py (5 tests) .................................... PASSED
tests/test_geo_utils.py (3 tests) ....................................... PASSED
tests/test_ml_inference.py (6 tests) .................................... PASSED
tests/test_phase4a_audit.py (7 tests) ................................... PASSED
tests/test_phase4b_audit.py (6 tests) ................................... PASSED
tests/test_phase4c_ml.py (8 tests) ...................................... PASSED
tests/test_phase4d_models.py (6 tests) .................................. PASSED
tests/test_sentinel2_change.py (12 tests) ............................... PASSED
tests/test_sentinel2_client.py (9 tests) ................................ PASSED
tests/test_sentinel2_patch_retriever.py (14 tests) ...................... PASSED
tests/test_sentinel2_real_processor.py (9 tests) ........................ PASSED
tests/test_sentinel2_recovery.py (4 tests) .............................. PASSED
tests/test_sentinel2_scale_633.py (8 tests) ............................. PASSED
tests/test_sentinel2_smoketest.py (7 tests) ............................. PASSED
tests/test_sentinel2_spectral.py (11 tests) ............................. PASSED
tests/test_weak_labeler.py (2 tests) .................................... PASSED

====================== 138 passed, 25 warnings in 11.70s ======================
```

---

## 11. Overall PASS/FAIL Conclusion

### Verdict: **PASS**

1. The FastAPI ML backend successfully completed live localhost smoke testing against real 633-event data.
2. Inference output matches direct Python `src/models/predict.py` calls with 100% precision.
3. Authentication, input validation, leakage blocking, and error envelopes operate strictly according to `outputs/phase_5c_api/ML_API_CONTRACT.md`.
4. Production model files remained completely untouched and verified by SHA-256 digest.
5. All 138 tests in the repository pass cleanly.

---
*End of Smoke Test Report.*
