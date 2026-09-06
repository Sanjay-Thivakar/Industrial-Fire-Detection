# FRONTEND / GIS INTEGRATION & HANDOFF GUIDE
## Industrial Fire Detection — Dashboard & ML API Integration (Phase 5C)

**Document Version:** 1.0.0  
**Target Audience:** Frontend Developers, GIS Engineers, UI/UX Designers  
**Backend Reference:** FastAPI ML Service (`src/api/main.py`)  
**Authoritative Dashboard Data:** `outputs/phase_5b_dashboard/dashboard_events_633.csv` (633 rows, 61 columns)  
**API Documentation Contract:** `outputs/phase_5c_api/ML_API_CONTRACT.md`  
**API Status:** Tested and Verified (138/138 Pytest Tests Passed)  

---

## 1. System Architecture

The following diagram illustrates the decoupled client-server architecture of the system:

```
┌────────────────────────────────────────────────────────┐
│                   FRONTEND & GIS UI                    │
│   (React / Vue / Leaflet / MapLibre / Vanilla JS)      │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            │ 1. Initial / Historical View   │ 2. Live On-Demand Inference
            │    (Read Static CSV)           │    (HTTP POST /api/v1/predict)
            ▼                                ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│    DASHBOARD EVENT DATA      │ │         FASTAPI SERVICE      │
│  `dashboard_events_633.csv`  │ │       `src/api/main.py`      │
│     (633 events, 61 cols)    │ └──────────────┬───────────────┘
└──────────────────────────────┘                │ Calls Python function
                                                ▼
                                 ┌──────────────────────────────┐
                                 │     INFERENCE INTERFACE      │
                                 │    `src/models/predict.py`   │
                                 └──────────────┬───────────────┘
                                                │ Evaluates Pipeline
                                                ▼
                                 ┌──────────────────────────────┐
                                 │   PRODUCTION RANDOM FOREST   │
                                 │     `final_model.joblib`     │
                                 │   (SHA-256: 5909bb546f...)   │
                                 └──────────────────────────────┘
```

> [!CRITICAL]
> **FRONTEND MUST NOT LOAD THE MODEL DIRECTLY:**  
> The production ML model (`final_model.joblib`) is a Python-serialized `scikit-learn` Pipeline containing internal ColumnTransformers, custom imputation statistics, and trained decision trees. The frontend application must **never** attempt to parse, deserialize, or load `.joblib` files directly in JavaScript. All inference queries must be dispatched over standard HTTP to the FastAPI endpoints.

---

## 2. API Connection & Endpoints

The backend exposes two REST endpoints under the `/api/v1` namespace.

- **Base URL (Local Development):** `http://127.0.0.1:8000`
- **Request Format:** `application/json; charset=utf-8`
- **Authentication:** `X-API-Key` HTTP Header (required for `/predict`)

### 2.1 Liveness & Readiness Endpoint: `GET /api/v1/health`

Use this endpoint to verify that the backend server is running and the production model is loaded in memory.

- **Method:** `GET`
- **Endpoint:** `/api/v1/health`
- **Authentication:** None (Public)

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

*If `model_loaded` is `false`, the API returns HTTP 503 (`status: "unavailable"`). The frontend should display a maintenance banner and disable live prediction triggers.*

---

### 2.2 Live Prediction Endpoint: `POST /api/v1/predict`

Executes 3-class ML inference for a single thermal anomaly event.

- **Method:** `POST`
- **Endpoint:** `/api/v1/predict`
- **Headers:**
  - `Content-Type: application/json`
  - `X-API-Key: <configured_api_key>`

#### Request Structure:
```json
{
  "event_id": "FIRMS_TN_LIVE_001",
  "features": {
    "frp": 2.45,
    "brightness": 322.8,
    "bright_t31": 296.1,
    "brightness_difference": 26.7,
    "frp_brightness_ratio": 0.0076,
    "log_frp": 1.238,
    "confidence_numeric": 2,
    "is_day": 1,
    "grid_detection_count": 14,
    "grid_active_days": 9,
    "persistent_location_flag": 1,
    "grid_total_frp": 42.1,
    "grid_brightness_mean": 319.4,
    "high_brightness_flag_local": 0,
    "high_frp_flag_local": 0,
    "brightness_zscore_local": 0.38,
    "frp_zscore_local": -0.11,
    "is_stubble_burning_season": 0,
    "landcover_code": 50,
    "distance_to_facility_m": 180.2,
    "nearest_facility_type": "industrial",
    "nearest_facility_category": "Steel / Metallurgy",
    "nearest_facility_tier": "HIGHER_RELEVANCE",
    "near_industrial_500m": 1,
    "near_industrial_1000m": 1,
    "near_industrial_2000m": 1,
    "near_industrial_5000m": 1,
    "near_industrial_10000m": 1,
    "distance_to_higher_relevance_m": 180.2,
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

#### Response Structure (HTTP 200 OK):
```json
{
  "event_id": "FIRMS_TN_LIVE_001",
  "predicted_class": "Industrial Thermal Activity",
  "probabilities": {
    "Agricultural Burning": 0.0412,
    "Industrial Thermal Activity": 0.9254,
    "Natural / Wildfire / Other": 0.0334
  },
  "max_probability": 0.9254,
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
  "inference_timestamp": "2026-09-06T18:18:49Z",
  "disclaimer": "Prediction is an algorithmic ML estimate. It is not ground truth."
}
```

---

### 2.3 Uniform Error Structure

All error responses from the API adhere to a standardized contract envelope:

```json
{
  "error": {
    "code": "<ERROR_CODE>",
    "message": "<Human-readable error explanation>",
    "details": {}
  }
}
```

| HTTP Status | Error Code | Trigger | Frontend Action |
|---|---|---|---|
| **400** | `INVALID_JSON` | Body is malformed JSON | Check payload serialization |
| **400** | `MISSING_FEATURES_OBJECT` | `features` key missing | Ensure payload wraps fields in `{ "features": { ... } }` |
| **401** | `MISSING_API_KEY` | Missing `X-API-Key` header | Prompt operator for API key or check env config |
| **403** | `INVALID_API_KEY` | Key mismatch | Verify active API key |
| **422** | `MISSING_REQUIRED_FEATURES` | Missing one of the 36 fields | Inspect `error.details.missing` for omitted fields |
| **422** | `LEAKAGE_FIELD_DETECTED` | Ground-truth labels included | Strip all human labels (`human_*`, `ml_target_3class`) |
| **422** | `INVALID_FEATURE_TYPE` | Data type uncoercible | Check `error.details.invalid_fields` |
| **500** | `INFERENCE_ERROR` | Runtime model failure | Display retry button; check backend logs |
| **503** | `MODEL_NOT_LOADED` | Model artifact unready | Display backend offline indicator |

---

## 3. Prediction Request Rules

1. **Required Features:** Exactly the **36 baseline features** derived from NASA FIRMS, OSM industrial data, and ESA WorldCover.
2. **Sentinel-2 Rasters NOT Required:** The frontend must **never** request, upload, or process Sentinel-2 GeoTIFFs or spectral arrays for ML inference.
3. **No Target Leakage Allowed:** Never send ground-truth fields (`human_ground_truth_class`, `human_raw_label`, `ml_target_3class`, `human_validation_status`, etc.). The API strictly rejects requests containing these fields with HTTP 422 `LEAKAGE_FIELD_DETECTED`.
4. **`event_id` is Optional:** The frontend can supply an `event_id` string for request correlation. It is echoed back verbatim in the response.

---

## 4. Prediction Response & Visual Guidelines

When rendering predictions in the UI:

| API Response Field | Frontend Component | Presentation Recommendation |
|---|---|---|
| `predicted_class` | Primary Badge / Title | Display prominently as **"ML Prediction: [Class]"**. Never label it simply as "Ground Truth" or "Fact". |
| `probabilities` | Tri-Color Bar Chart | Render 3 horizontal stacked or segmented bars showing all 3 class probabilities simultaneously. |
| `max_probability` | Percentage Metric | Display as percentage: e.g., `92.5%` (`round(max_probability * 100, 1)`). |
| `ml_confidence` | Status Indicator | Color code: **HIGH** (`#10B981` / Green), **MEDIUM** (`#F59E0B` / Amber), **LOW** (`#EF4444` / Red). |
| `confidence_scale` | Tooltip Info | Show threshold rules in hover tooltip: HIGH (≥75%), MEDIUM (50–74%), LOW (<50%). |
| `disclaimer` | Footer Caption | Include the exact disclaimer text: *"Prediction is an algorithmic ML estimate. It is not ground truth."* |

> [!WARNING]
> **ML CONFIDENCE IS NOT GROUND TRUTH:**  
> A prediction with `ml_confidence: "HIGH"` indicates only that the Random Forest model assigned a high mathematical probability (≥ 0.75) based on tabular spatial and thermal features. It does not constitute field verification or eyewitness confirmation.

---

## 5. Dashboard Data Package (`dashboard_events_633.csv`)

For the primary interactive dashboard, use the pre-built, audited dataset:  
**File Path:** `outputs/phase_5b_dashboard/dashboard_events_633.csv`  
**Records:** Exactly 633 verified thermal events across Tamil Nadu  
**Columns:** 61 clean, standardized fields across 9 logical groups  

### 5.1 Essential Fields for Map Rendering

| Field Name | Type | Purpose / UI Mapping |
|---|---|---|
| `event_id` | `string` | Unique identifier (e.g., `FIRMS_TN_0000`). Marker key. |
| `latitude` | `float` | WGS84 Latitude coordinate (100% complete, zero nulls). |
| `longitude` | `float` | WGS84 Longitude coordinate (100% complete, zero nulls). |
| `predicted_class` | `string` | Primary marker category (Industrial, Agricultural, Natural). |
| `ml_confidence` | `string` | Marker outline or opacity tier (`HIGH`, `MEDIUM`, `LOW`). |
| `max_probability` | `float` | Marker size scaling or hover popup metric. |
| `firms_confidence` | `string` | Satellite thermal confidence (`h` = high, `n` = nominal, `l` = low). |

---

### 5.2 Fields for the Event Details Drawer / Inspector

When an operator clicks a marker on the map, open an event details panel populated with the following 61 fields:

#### A. Temporal & Acquisition Details (Group A)
- `acq_date` (Date, e.g., `2024-11-01`)
- `acq_time` (UTC time, e.g., `1940`)
- `acq_datetime` (Full ISO timestamp)
- `daynight` (`D` = Daytime, `N` = Nighttime)

#### B. Thermal Signal Quality (Group C)
- `satellite` (`N20`, `NOAA-21`, `SNPP`)
- `instrument` (`VIIRS`)
- `firms_confidence` (`h`, `n`, `l`)
- `frp` (Fire Radiative Power in MW — primary intensity metric)
- `brightness` (I4 channel brightness temperature in Kelvin)
- `bright_t31` (I5 channel brightness temperature in Kelvin)
- `brightness_difference` (I4 - I5 difference in Kelvin)
- `is_stubble_burning_season` (`1` = active season, `0` = off-season)

#### C. Spatial Persistence & Recurrence (Group C)
- `grid_detection_count` (Historical detections in 0.05° grid cell)
- `grid_active_days` (Distinct days of activity in grid cell)
- `persistent_location_flag` (`1` if `grid_active_days >= 3`, else `0`)
- `grid_total_frp` (Cumulative FRP across cell)
- `high_frp_flag_local` (`1` if local anomaly spike)
- `brightness_zscore_local` (Standardized brightness score)

#### D. Industrial & Spatial Context (Group E)
- `nearest_facility_name` (Name from OpenStreetMap; display `"Unknown"` if null)
- `nearest_facility_type` (OSM primary tag, e.g., `industrial`, `quarry`, `substation`)
- `nearest_facility_category` (Broad sector, e.g., `Steel / Metallurgy`, `Manufacturing`, `Textile`)
- `nearest_facility_tier` (`HIGHER_RELEVANCE`, `CAUTION_LOWER_RELEVANCE`, `GENERAL_CONTEXT`)
- `distance_to_facility_m` (Euclidean distance in meters to nearest facility)
- `near_industrial_500m`, `near_industrial_1000m`, `near_industrial_2000m` (Binary proximity flags)
- `nearest_hr_category` & `nearest_hr_name` (Nearest high-relevance facility details)
- `distance_to_higher_relevance_m` (Meters to nearest high-relevance facility)
- `osm_coverage_status` (`COVERED` vs `FAILED_TILE`)

#### E. Land Surface Context (Group F)
- `landcover_code` (ESA WorldCover numerical code)
- `landcover_class` (Descriptive name: `Built-up`, `Cropland`, `Tree cover`, `Grassland`, `Shrubland`, `Bare / sparse vegetation`)

#### F. Supporting Sentinel-2 Evidence (Group G)
- `pre_observation_status` (`REAL_CDSE_SUCCESS`, `CLOUD_REJECTED`, `MISSING_PRODUCT`)
- `post_observation_status` (`REAL_CDSE_SUCCESS`, `CLOUD_REJECTED`, `MISSING_PRODUCT`)
- `s2_change_status` (`SUCCESS`, `MISSING_POST`, `MISSING_PRE`, `INSUFFICIENT_VALID_DATA`)
- `selected_pre_image_date` & `selected_post_image_date` (Observation acquisition dates)
- `s2_pre_ndvi_mean` & `s2_post_ndvi_mean` (Pre/post vegetation vigor; display `"N/A"` if null)
- `s2_dnbr_mean` (Normalized Burn Ratio difference; display `"N/A"` if null)

#### G. Human Verification Status (Group H)
- `has_human_validation` (`true` / `false` — indicates whether manual ground-truth was conducted)
- `human_validation_status` (`VALIDATED` vs `UNVALIDATED`)
- `human_ground_truth_class` (Class label assigned during expert review; display `"Not reviewed"` for the 84.2% unreviewed events)
- `is_unambiguous_ground_truth` (`true` / `false`)

---

### 5.3 Recommended Multi-Facet Filters

Build filters using **ONLY** the following fields verified to exist in `dashboard_events_633.csv`:

1. **Prediction Class Filter:** Multiselect for `predicted_class` (`Industrial Thermal Activity`, `Agricultural Burning`, `Natural / Wildfire / Other`).
2. **ML Confidence Tier:** Checkboxes for `ml_confidence` (`HIGH`, `MEDIUM`, `LOW`).
3. **FIRMS Sensor Confidence:** Filter by `firms_confidence` (`h` - High, `n` - Nominal, `l` - Low).
4. **Day / Night:** Toggle for `daynight` (`D`, `N`).
5. **Landcover Type:** Multiselect for `landcover_class` (`Built-up`, `Cropland`, `Tree cover`, `Grassland`, etc.).
6. **Industrial Proximity Tier:** Filter by `nearest_facility_tier` (`HIGHER_RELEVANCE`, `CAUTION_LOWER_RELEVANCE`, `GENERAL_CONTEXT`, `NO_FACILITY_FOUND`).
7. **Spatial Persistence:** Toggle for `persistent_location_flag` (`1` = Multi-day hotspot, `0` = Single-day event).
8. **Human Validation Badge:** Filter events with `has_human_validation == true`.
9. **FRP Range Slider:** Continuous slider bound between `min(frp)` (~0.3 MW) and `max(frp)` (~40.0+ MW).
10. **Sentinel-2 Data Availability:** Filter by `s2_change_status == "SUCCESS"` to highlight events with verified optical change evidence.

---

## 6. Three-Class ML vs Six-Class Research Taxonomy

To maintain scientific integrity during demonstrations, the frontend team must understand the distinction between the ML model outputs and the human ground-truth taxonomy:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      HUMAN GROUND TRUTH TAXONOMY (6 CLASSES)                     │
├────────────────────────────────┬─────────────────────────────────────────────────┤
│ Persistent Industrial Source   │ High-confidence recurring factory / smelter     │
│ Episodic Industrial Activity   │ Sporadic industrial furnace / boiler anomaly    │
├────────────────────────────────┼─────────────────────────────────────────────────┤
│ Agricultural / Crop Residue    │ Seasonal stubble / field burning                │
├────────────────────────────────┼─────────────────────────────────────────────────┤
│ Forest / Wildfire              │ Vegetative wildfire / forest blaze              │
│ Other Natural / Land Clearing  │ Non-crop natural thermal signature              │
├────────────────────────────────┼─────────────────────────────────────────────────┤
│ Review Required / Ambiguous    │ Unresolved or ambiguous satellite observation   │
└────────────────────────────────┴─────────────────────────────────────────────────┘
                                         ▼
                 [Consolidated for Robust Machine Learning]
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                       PRODUCTION ML MODEL (3 OFFICIAL CLASSES)                   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 1. Industrial Thermal Activity                                                   │
│    (Includes BOTH Persistent and Episodic Industrial facilities)                 │
│ 2. Agricultural Burning                                                          │
│ 3. Natural / Wildfire / Other                                                    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Critical Rules for Frontend Display:
1. **Never invent 6-class ML predictions:** The model produces exactly 3 classes. The frontend must **never** attempt to split `Industrial Thermal Activity` into sub-classes using custom rules or heuristics.
2. **Displaying "Persistent Industrial Thermal Source":** If an event has `has_human_validation == true` and `human_ground_truth_class == "Persistent Industrial Thermal Source"`, show this in the **Human Validation Card** as an expert ground-truth note, while the **ML Prediction Card** continues to report `Industrial Thermal Activity`.

---

## 7. Disambiguating the Three Confidence Metrics

The dashboard dataset contains three distinct confidence metrics that must **never** be conflated:

| Column Name | Source | Range / Values | Meaning | UI Label |
|---|---|---|---|---|
| `firms_confidence` | NASA FIRMS VIIRS Sensor | `l` (Low), `n` (Nominal), `h` (High) | Radiometric certainty that a real hot spot exists on the ground (vs noise/cloud reflection). | **"Satellite Sensor Confidence"** |
| `max_probability` | Scikit-learn Random Forest | `0.0000` – `1.0000` (Continuous) | Direct mathematical probability assigned to the winning predicted class. | **"Winning Probability"** |
| `ml_confidence` | Probability Categorization Rule | `HIGH` (≥0.75), `MEDIUM` (0.50–0.74), `LOW` (<0.50) | Categorical confidence tier of the ML classification. | **"ML Model Confidence"** |

---

## 8. Accurate Presentation of Sentinel-2 Optical Evidence

When presenting Sentinel-2 data in the event drawer:

1. **Supporting Surface Context Only:** Sentinel-2 multispectral MSI is an optical/near-infrared instrument (10m–20m resolution). It captures pre-event and post-event surface reflectance.
2. **Do NOT Describe Sentinel-2 as Thermal Detection:** Sentinel-2 does **not** provide thermal infrared plume measurements. The thermal detection originates strictly from the 375m VIIRS sensor (FIRMS).
3. **Handling High Cloud Rejection:** Over 40% of Sentinel-2 scenes in Tamil Nadu have cloud interference (`pre_observation_status == "CLOUD_REJECTED"`). When spectral fields (`s2_dnbr_mean`, `s2_pre_ndvi_mean`) are null, explain gracefully: *"Optical imagery obstructed by cloud cover during satellite overpass."*
4. **Interpreting dNBR:** Where available, positive `s2_dnbr_mean` (> 0.1) indicates surface vegetation burn or clearing. In built-up industrial zones, dNBR is typically near zero (`~0.0`), indicating fixed structural operations without surrounding vegetative burn scars.

---

## 9. Static Dataset vs Live API Workflow

| Capability | Static Dataset (`dashboard_events_633.csv`) | Live API (`POST /api/v1/predict`) |
|---|---|---|
| **Primary Use Case** | Initial load, comprehensive map view, historical analytics, filtering. | On-demand evaluation of new incoming FIRMS alerts or hypothetical test cases. |
| **Data Scope** | 633 verified Tamil Nadu thermal events. | Single event per request. |
| **Latency** | Instant (local CSV/JSON load). | ~15–30 ms network roundtrip. |
| **Authentication** | None needed (bundled asset). | Requires `X-API-Key` header. |
| **Sentinel-2 Data** | Pre-computed status and spectral means included. | Not accepted or evaluated. |
| **External Credentials** | Zero NASA FIRMS or Copernicus CDSE credentials required. | Zero external credentials required. |

---

## 10. Ownership Matrix

### Frontend / GIS Team Owns:
- Map framework initialization (Leaflet, MapLibre, Mapbox GL).
- Custom markers, color encodings, SVG icons, and cluster groups.
- Filter drawer, range sliders, search bar, and active filter pill tags.
- Event detail modal / slide-over inspector drawer.
- Charting widgets (probability distribution bars, FRP distribution histograms).
- Integration of `fetch()` / `axios` calls to `/api/v1/predict` and `/api/v1/health`.
- Handling UI loading states, network skeletons, and error dialogs.

### Backend Team Owns:
- Model artifact storage, deserialization, and SHA-256 integrity verification.
- Feature schema completeness check (36 baseline features).
- Feature type coercion, missing-feature validation, and target-leakage guarding.
- Execution of Scikit-learn Pipeline inference.
- API authentication enforcement (`X-API-Key`).
- Health check reporting and structured error envelope responses.

---

## 11. SIH Jury Demonstration Script (Step-by-Step)

Follow this narrative flow during the Smart India Hackathon jury presentation:

1. **Launch Dashboard:** Open the web application. Show the 633 detected thermal anomaly hotspots plotted across Tamil Nadu.
2. **Display Health Status:** Highlight the green status indicator in the navbar: *"ML Backend Online — Model SHA-256 Verified (Random Forest Pipeline)"*.
3. **Filter Industrial Candidates:** Apply the filter:
   - Landcover: `Built-up`
   - Facility Tier: `HIGHER_RELEVANCE`
   - Persistence: `Persistent Hotspot (>= 3 active days)`
   - Show how the map filters down to major industrial complexes (e.g., Salem Steel Plant, thermal power stations, petrochemical plants).
4. **Select Event `FIRMS_TN_0000`:** Click the marker located near the Salem Steel facility.
5. **Inspect Multi-Source Evidence:**
   - **FIRMS:** VIIRS 375m detection, FRP = 1.16 MW, persistent location flag active.
   - **OSM Context:** Nearest facility = SAIL / Salem Steel Plant (328 meters away, `HIGHER_RELEVANCE`).
   - **WorldCover:** Surface class = `Built-up` (Class 50).
   - **Sentinel-2:** Optical change status verified.
6. **Reveal 3-Class ML Prediction:**
   - Predicted Class: **Industrial Thermal Activity**
   - Probability Bar: Industrial `50.3%`, Agricultural `43.3%`, Natural `6.4%`
   - ML Confidence: **MEDIUM**
7. **Explain Multi-Modal Classification Logic:** Explain that the model correctly identified industrial thermal activity by fusing the persistent multi-day thermal signature with 328m proximity to a known steel plant on built-up land.
8. **Distinguish Prediction from Ground Truth:** Point to the human review badge: *"Validated Ground Truth: Persistent Industrial Thermal Source"*. Emphasize that the ML prediction is an automated assistive tool, and human validation confirmed its accuracy.

---

## 12. Frontend Integration Checklist

Before declaring frontend integration complete, verify every item below:

- [ ] **Data Source:** Dashboard loads all 633 records from `outputs/phase_5b_dashboard/dashboard_events_633.csv`.
- [ ] **Zero Coordinates Lost:** Exactly 633 markers appear on the map at valid Tamil Nadu coordinates.
- [ ] **No Direct Joblib Access:** Codebase confirmed to contain zero imports or reads of `.joblib` files.
- [ ] **Health Check Polling:** UI queries `GET /api/v1/health` on startup and reflects backend liveness.
- [ ] **API Key Configuration:** Frontend stores `X-API-Key` in an environment variable (e.g. `VITE_API_KEY` or `REACT_APP_API_KEY`); never hardcoded in public repository files.
- [ ] **Prediction Header:** `POST /api/v1/predict` includes `Content-Type: application/json` and `X-API-Key`.
- [ ] **Target Leakage Shield:** UI never passes `human_*` or `ml_target_3class` columns to the API.
- [ ] **Three-Class Display:** UI renders exactly the 3 production classes; does not fabricate sub-classes.
- [ ] **Probability Bars:** All 3 probabilities (`Industrial`, `Agricultural`, `Natural`) are rendered simultaneously.
- [ ] **Confidence Disambiguation:** `firms_confidence` (sensor) and `ml_confidence` (model) are clearly labeled as separate metrics.
- [ ] **Sentinel-2 Accuracy:** Sentinel-2 is presented strictly as optical/surface evidence, not as a thermal plume detector.
- [ ] **Null Safety:** Handled nulls gracefully for `nearest_facility_name` (Unknown), `human_ground_truth_class` (Not reviewed), and `s2_dnbr_mean` (N/A).
- [ ] **Disclaimer Visible:** Prediction inspector displays the mandatory disclaimer string.

---
*End of Frontend / GIS Integration Handoff Guide.*
