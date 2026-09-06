# BACKEND SETUP & DEVELOPER HANDOFF GUIDE
## Industrial Fire Detection — Machine Learning Inference API (Phase 5C)

**Document Version:** 1.0.0  
**Target Application:** FastAPI Production ML Inference API (`src/api/main.py`)  
**Production Model:** Baseline 3-Class Random Forest (`outputs/phase_5_ml_handoff/final_model.joblib`)  
**SHA-256 Digest:** `5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798`  

---

## 1. Prerequisites

Before setting up the API, ensure the following tools are installed on your host system:
- **Python**: Version 3.10 or 3.11 (Python 3.11 recommended; 64-bit)
- **pip**: Version 22.0 or newer
- **Git**: For source repository management

> **Note on Hardware / Dependencies:**  
> The inference service runs efficiently on standard CPU architectures. No GPU or CUDA drivers are required. Optical satellite raster processing (Sentinel-2) is pre-computed and **not required** at inference time.

---

## 2. Virtual Environment Setup

Always use an isolated Python virtual environment to avoid package version conflicts.

### Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Windows (Command Prompt):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

---

## 3. Dependency Installation

Install all required dependencies using the pinned project `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Core API Packages Installed:
- `fastapi>=0.111.0`: High-performance asynchronous API framework
- `uvicorn[standard]>=0.29.0`: Production-ready ASGI server
- `pydantic>=2.7.0`: Data validation and settings management
- `httpx>=0.27.0`: HTTP client library for integration testing
- `scikit-learn>=1.0.0`, `joblib>=1.0.0`, `pandas`, `numpy`: ML inference dependencies

---

## 4. Environment Variables Configuration

The ML inference API uses environment variables to configure authentication and runtime behavior.

1. Copy the template `.env.example` file to `.env`:
   ```bash
   cp .env.example .env      # Linux / macOS
   copy .env.example .env    # Windows CMD
   Copy-Item .env.example .env # Windows PowerShell
   ```

2. Configure the following variables in `.env` (or in your deployment environment):

| Variable | Required | Default / Fallback | Description |
|---|---|---|---|
| `ML_API_KEY` | **Yes** (Production) | `test-api-key-phase5c` | Secret token required in the `X-API-Key` header for `POST /api/v1/predict` |
| `API_KEY` | Alternative | — | Accepted as fallback if `ML_API_KEY` is not set |
| `API_HOST` | Optional | `127.0.0.1` | Local network binding address |
| `API_PORT` | Optional | `8000` | Port number for Uvicorn |

> [!CAUTION]
> **Security Rule:** NEVER commit a `.env` file containing real keys to Git or any public repository. `.env` is ignored by `.gitignore`.

---

## 5. How to Start the API Locally

Run Uvicorn from the root directory of the repository, binding strictly to localhost:

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Or run via Python module syntax:
```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

### Startup Output Confirmation:
Upon launch, Uvicorn will trigger the FastAPI `lifespan` handler, which pre-loads the model artifact and verifies its SHA-256 checksum:
```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Loading production model from: outputs/phase_5_ml_handoff/final_model.joblib
INFO:     Production model loaded successfully. SHA-256: 5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

- **Local Base URL:** `http://127.0.0.1:8000`
- **Interactive OpenAPI Documentation (Swagger):** `http://127.0.0.1:8000/docs`
- **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`

---

## 6. Endpoints & Usage

### 6.1 Liveness & Readiness Check: `GET /api/v1/health`

- **URL:** `http://127.0.0.1:8000/api/v1/health`
- **Method:** `GET`
- **Authentication:** None (Public)
- **Purpose:** Used by container orchestrators (Kubernetes / Docker healthchecks), frontend clients, and load balancers to verify service availability.

#### Example curl command:
```bash
curl -X GET http://127.0.0.1:8000/api/v1/health
```

#### Expected 200 OK Response:
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

#### Meaning of Health Fields:
- `status: "ok"`: Server is operational.
- `model_loaded: true`: Scikit-learn Pipeline is loaded in memory and ready to evaluate vectors.
- `model_sha256`: Digest of the active model matches the cryptographic baseline.
- `required_features_count: 36`: Expected feature vector dimensionality.
- `production_classes`: The three classes output by the classifier.

---

### 6.2 Prediction Endpoint: `POST /api/v1/predict`

- **URL:** `http://127.0.0.1:8000/api/v1/predict`
- **Method:** `POST`
- **Headers:**
  - `Content-Type: application/json`
  - `X-API-Key: <your_secret_key>`
- **Authentication:** Mandatory via `X-API-Key`

#### Example curl command:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_local_development_key_here" \
  -d '{
    "event_id": "FIRMS_TN_SAMPLE_001",
    "features": {
      "frp": 1.16,
      "brightness": 311.1,
      "bright_t31": 287.43,
      "brightness_difference": 23.67,
      "frp_brightness_ratio": 0.0037,
      "log_frp": 0.77,
      "confidence_numeric": 1,
      "is_day": 0,
      "grid_detection_count": 3,
      "grid_active_days": 2,
      "persistent_location_flag": 0,
      "grid_total_frp": 3.8,
      "grid_brightness_mean": 308.5,
      "high_brightness_flag_local": 0,
      "high_frp_flag_local": 0,
      "brightness_zscore_local": -0.12,
      "frp_zscore_local": -0.05,
      "is_stubble_burning_season": 0,
      "landcover_code": 50,
      "distance_to_facility_m": 328.3,
      "nearest_facility_type": "industrial",
      "nearest_facility_category": "Steel / Metallurgy",
      "nearest_facility_tier": "HIGHER_RELEVANCE",
      "near_industrial_500m": 1,
      "near_industrial_1000m": 1,
      "near_industrial_2000m": 1,
      "near_industrial_5000m": 1,
      "near_industrial_10000m": 1,
      "distance_to_higher_relevance_m": 328.3,
      "nearest_hr_category": "Steel / Metallurgy",
      "near_higher_relevance_500m": 1,
      "near_higher_relevance_1000m": 1,
      "near_higher_relevance_2000m": 1,
      "near_higher_relevance_5000m": 1,
      "near_higher_relevance_10000m": 1,
      "osm_coverage_status": "COVERED"
    }
  }'
```

#### Expected 200 OK Response:
```json
{
  "event_id": "FIRMS_TN_SAMPLE_001",
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

---

## 7. Running Tests

### 7.1 Running API Integration Tests Only:
```bash
pytest -v tests/test_api.py
```
*Expected: 11 tests passed.*

### 7.2 Running ML Inference Interface Tests:
```bash
pytest -v tests/test_ml_inference.py
```
*Expected: 6 tests passed.*

### 7.3 Running the Full Test Suite:
```bash
pytest -v
```
*Expected: 138 tests passed across the entire repository.*

---

## 8. Security & Production Deployment Guidance

> [!CRITICAL]
> **DO NOT EXPOSE THIS API PUBLICLY WITHOUT PROPER INFRASTRUCTURE SECURITY.**  
> The development server (`uvicorn src.api.main:app`) is intended strictly for local development and integration testing bound to `127.0.0.1`.

### Production Deployment Requirements:
1. **Reverse Proxy & TLS Termination:**
   - Always run behind a production reverse proxy (e.g., NGINX, Traefik, AWS ALB, Caddy).
   - Enforce HTTPS/TLS 1.3 encryption. Reject all plaintext HTTP traffic.
2. **Strict Network Binding:**
   - Bind Uvicorn to an internal private socket or localhost loopback (`127.0.0.1` or unix domain socket). Never bind directly to `0.0.0.0` on a public internet interface.
3. **CORS Hardening:**
   - Configure CORS middleware in production to allow only vetted dashboard / frontend origin domains.
4. **Rate Limiting:**
   - Implement rate limiting (e.g. 100 requests/minute per client IP / API key) at the reverse proxy or API gateway layer.
5. **Secret Rotation:**
   - Provide `ML_API_KEY` via a secure secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, Kubernetes Secret). Do not store secrets in configuration files.
6. **Data Leakage Guard:**
   - The API strictly enforces a leakage block against ground truth / human validation labels (e.g. `human_ground_truth_class`, `ml_target_3class`). Any attempts to pass label fields return HTTP 422 `LEAKAGE_FIELD_DETECTED`.
7. **Model Tamper Guard:**
   - If the model file on disk is modified or replaced without updating the pinned hash, the server startup sequence will identify the discrepancy.

---
*End of Backend Setup Guide.*
