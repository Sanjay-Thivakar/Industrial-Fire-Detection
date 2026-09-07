# AI Industrial Fire & Persistent Thermal Source Detection System

**Smart India Hackathon (SIH) 2026 Solution**  
*AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, Sentinel-2, OpenStreetMap & ESA WorldCover Data*

---

## 1. System Overview & Problem Statement

Satellite sensors like NASA VIIRS detect thermal anomalies globally with high temporal frequency. However, raw satellite thermal detections alone cannot reliably differentiate between:
1. **Industrial Thermal Activity**: Stationary industrial heat signatures (foundries, refineries, flare stacks, cement kilns, brick kilns) or catastrophic industrial fires.
2. **Agricultural Burning**: Ephemeral open-field crop residue burning or post-harvest stubble clearance.
3. **Natural / Wildfire / Other**: Forest blazes, scrubland fires, brush fires, or unclassified open burning.

This system provides an end-to-end, multi-modal operational platform combining satellite thermal observations (NASA FIRMS VIIRS), high-resolution land cover (ESA WorldCover 10 m), OpenStreetMap (OSM) industrial infrastructure context, and high-resolution optical surface change evidence (Copernicus Sentinel-2 MSI). It delivers predictions via a production **FastAPI inference service** and visualizes 633 curated events across Tamil Nadu via a **React 19 + TypeScript GIS dashboard**.

> [!IMPORTANT]
> **Mandatory Scientific Disclaimer**:  
> **"Prediction is an algorithmic ML estimate. It is not ground truth."**  
> All model predictions represent algorithmic probability distributions. The system explicitly separates satellite sensor detections, geographic context, human expert ground truth, and machine learning inferences.

---

## 2. Machine Learning Architecture & Official Classes

The production classifier operates on **three official, mutually exclusive classes**:

1. **`Industrial Thermal Activity`**: Stationary operational high-temperature heat sources (e.g. brick kilns, refinery flaring, smelters) and accidental industrial fires.
2. **`Agricultural Burning`**: Post-harvest seasonal crop residue / stubble burning in cultivated fields.
3. **`Natural / Wildfire / Other`**: Forest fires, scrubland combustion, and unclassified non-industrial burning.

### 2.1 Why 3 Classes Instead of 6 Classes?
A forensic statistical audit in Phase 4B evaluated a 6-class human taxonomy on 100 reviewed events. Because minority classes had extreme sample scarcity (`Industrial Fire`: 3 events, `Other/Unclassified`: 2 events), training a 6-class supervised model was mathematically invalid (stratified 5-fold cross-validation requires $\ge 5$ samples per class). Consolidating into a 3-class target reduced class imbalance from $25:1$ to $4.55:1$, enabling rigorous, reproducible stratified evaluation.

### 2.2 Model Selection: Baseline (36 features) vs Sentinel-2 Enhanced (73 features)
The production model is a **Random Forest Classifier** (`n_estimators=100`, `max_depth=6`, `class_weight='balanced'`, `random_state=42`) trained strictly on the **36 Baseline Features**:
- **NASA FIRMS Thermal Intensity (8 features):** `frp`, `brightness`, `bright_t31`, `brightness_difference`, `frp_brightness_ratio`, `log_frp`, `confidence_numeric`, `is_day`.
- **NASA FIRMS Spatial-Temporal Persistence (10 features):** `grid_detection_count`, `grid_active_days`, `persistent_location_flag`, `grid_total_frp`, `grid_brightness_mean`, `high_brightness_flag_local`, `high_frp_flag_local`, `brightness_zscore_local`, `frp_zscore_local`, `is_stubble_burning_season`.
- **ESA WorldCover Land Cover (1 feature):** `landcover_code`.
- **OpenStreetMap Geospatial Proximity (17 features):** `distance_to_facility_m`, `nearest_facility_type`, `nearest_facility_category`, `nearest_facility_tier`, `near_industrial_500m` to `near_industrial_10000m`, `distance_to_higher_relevance_m`, `nearest_hr_category`, `osm_coverage_status`.

**Why Sentinel-2 Features Were Excluded from the Production Model:**  
In Phase 4D, an enhanced 73-feature model was compared against the 36-feature baseline under identical 5-fold cross-validation. Sentinel-2 features dropped out-of-fold Macro F1 from **0.7772** to **0.7531** (-0.0241 penalty) due to the curse of dimensionality on $n=76$ samples and physical optical missingness (40.1% cloud cover in Tamil Nadu). Both models achieved identical industrial recall (93.33%). The Baseline Random Forest was chosen because it is statistically superior, requires zero runtime API latency, and does not depend on cloud-free satellite passes.

---

## 3. Ground Truth & Model Performance

### 3.1 Human Ground Truth Cohort (`n=100`)
- **Total human-reviewed events:** 100.
- **Unambiguous ground truth (`n=76`):** 50 Agricultural Burning, 12 Persistent Industrial Sources, 9 Natural/Forest Fires, 3 Industrial Fires, 2 Other.
- **Held-out `REVIEW_REQUIRED` (`n=24`):** 13 uncertain agricultural burns, 6 ambiguous industrial anomalies, 5 borderline scrub burns. These were strictly excluded from model training to prevent label noise corruption.
- **Zero Synthetic Labels:** No weak labels or synthetic heuristics were converted into ground truth.

### 3.2 Out-of-Fold Cross-Validation Performance (76 events)
Evaluation was conducted using 5-fold stratified cross-validation with in-fold imputation and encoding (zero data leakage):

| Target Class | Support (True Events) | Recall | Precision | Class F1-Score |
|---|:---:|:---:|:---:|:---:|
| **Industrial Thermal Activity** | **15** | **93.33% (14/15)** | **87.50% (14/16)** | **0.9032** |
| **Agricultural Burning** | **50** | **92.00% (46/50)** | **88.46% (46/52)** | **0.9020** |
| **Natural / Wildfire / Other** | **11** | **45.45% (5/11)** | **62.50% (5/8)** | **0.5263** |
| **Macro Average** | **76** | **76.93%** | **79.49%** | **0.7772** |

> [!WARNING]
> **Performance Presentation Rules:**  
> - **93.33%** is the **Industrial Thermal Activity Recall**, NOT overall model accuracy!
> - **87.50%** is the **Industrial Thermal Activity Precision**, NOT overall model accuracy!
> - **0.7772** is the **Macro F1 score** across all three classes.
> - Model probabilities represent **uncalibrated ensemble voting proportions**, NOT statistical certainty.

---

## 4. Known Failure Modes & Error Analysis

The system documents all 11 out-of-fold misclassifications honestly rather than hiding errors:

### 4.1 Industrial False Negative (1 event: `FIRMS_TN_0176`)
- **True Label:** Industrial Thermal Activity (human label: `"Presistent Industrial Themal Souce"`).
- **Model Prediction:** Agricultural Burning (Prob: 0.885).
- **Physical Root Cause:** The human reviewer labeled this site as a persistent industrial source from external site knowledge, but in satellite observations for this cycle, the anomaly appeared on **only 1 active day** (`grid_active_days = 1`, `persistent_location_flag = 0`) with low FRP (4.52 MW) in tree cover. Because satellite persistence was completely absent, the model predicted Agricultural Burning.

### 4.2 Industrial False Positives (2 events: `FIRMS_TN_0093` and `FIRMS_TN_0258`)
- **`FIRMS_TN_0093`**: Agricultural burning persisting over **5 active days** in the same grid cell triggered `persistent_location_flag = 1`, misleading the model into predicting stationary industrial thermal activity.
- **`FIRMS_TN_0258`**: A multi-day forest wildfire active across **3 days** triggered the persistence flag, leading the model to assign an industrial classification.

---

## 5. Scientific Interpretation & Sensor Roles

| Source / Sensor | Physical Nature | Role in System | What It Is NOT |
|---|---|---|---|
| **NASA FIRMS (VIIRS)** | Thermal Infrared (375 m) | Primary anomaly detection; provides brightness, FRP, and grid persistence. | Does NOT confirm an industrial fire by itself. |
| **ESA WorldCover** | Radar + Optical Land Cover (10 m) | Provides ecological context (cropland, forest, built-up). | Does NOT confirm combustion or fire type. |
| **OpenStreetMap (OSM)** | Geospatial Vector Infrastructure | Contextual proximity evidence (distance to industrial facilities). | Proximity $\neq$ causality. Not ground truth. |
| **Copernicus Sentinel-2** | Optical Reflectance (VNIR/SWIR, 10–20 m) | Post-hoc optical surface/change evidence (dNDVI, dNBR, burn scars). | **NOT a thermal sensor.** Missing imagery does not imply no fire. |
| **Production Model** | Random Forest Classifier | Computes 3-class algorithmic probability distribution. | **NOT ground truth.** Output probabilities are uncalibrated. |

### 5.3 Candidate Population Selection Bias
Across the 633 curated statewide events:
- **45.3%** Agricultural Burning (287 events)
- **41.2%** Industrial Thermal Activity (261 events)
- **13.4%** Natural / Wildfire / Other (85 events)

The 41.2% industrial share in the 633 dataset is higher than the 19.7% training share because the candidate pool was spatially pre-selected near known industrial corridors in Tamil Nadu. **41.2% represents the candidate pool distribution, not the statewide baseline fire frequency.**

---

## 6. System Architecture & Tech Stack

```
                     +-------------------------------------------------------------+
                     |                     NASA FIRMS VIIRS                        |
                     |             Thermal Anomaly Detections (375m)               |
                     +------------------------------+------------------------------+
                                                    |
         +------------------------------------------+------------------------------------------+
         |                                          |                                          |
         v                                          v                                          v
+------------------+                      +--------------------+                     +--------------------+
|  ESA WorldCover  |                      |   OpenStreetMap    |                     | Copernicus S2 L2A  |
| 10m Land Cover   |                      | Geospatial Context |                     | Optical Validation |
+--------+---------+                      +---------+----------+                     +---------+----------+
         |                                          |                                          |
         +--------------------+---------------------+                                          |
                              v                                                                |
               +------------------------------+                                                |
               |  Exact 36-Feature Vector     |                                                |
               |  (Inference Pipeline)        |                                                |
               +--------------+---------------+                                                |
                              v                                                                |
               +------------------------------+                                                |
               |     FastAPI Backend          |                                                |
               |   POST /api/v1/predict       |                                                |
               |   Random Forest Classifier   |                                                |
               +--------------+---------------+                                                |
                              v                                                                |
               +------------------------------+                                                |
               |     Vite Server Proxy        |                                                |
               |   Server-Side Auth Header    |                                                |
               +--------------+---------------+                                                |
                              v                                                                |
               +------------------------------+                                                |
               |  React 19 + TS GIS Dashboard | <----------------------------------------------+
               |  Leaflet Map + Live Card     |       (Pre/Post optical burn scar verification)
               +------------------------------+
```

- **Backend**: FastAPI 0.111, Uvicorn 0.29, Pydantic v2, Scikit-Learn 1.6, Joblib 1.4.
- **Frontend**: React 19, TypeScript 5.7, Vite 8.2, Leaflet 1.9, Vanilla CSS design tokens.
- **Security**: Server-side proxy API key injection (`X-API-Key`); zero client-side key storage; CORS whitelisting.

---

## 7. Quick Start & Execution

### 7.1 Backend Setup
```bash
# 1. Activate virtual environment
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

# 2. Start FastAPI Inference Backend (Port 8000)
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```
- Verify health: `GET http://127.0.0.1:8000/api/v1/health`
- Swagger Docs: `http://127.0.0.1:8000/docs`

### 7.2 Frontend Development Server
```bash
cd frontend
npm install
npm run dev
```
- Open dashboard: `http://127.0.0.1:5173/`

### 7.3 Production Build & Preview
```bash
cd frontend
npm run build
npm run preview
```
- Open preview: `http://127.0.0.1:4173/`

### 7.4 Running Automated Verification Suites
```bash
# Backend Test Suite (142 tests)
pytest -v

# Frontend Test Suite (82 tests across 11 suites)
cd frontend && npm test
```

---

## 8. Artifacts & Reference Reports

- **Scientific Audit**: [`outputs/phase_8/PHASE_8_STEP_1_SCIENTIFIC_VALIDATION_AUDIT.md`](file:///outputs/phase_8/PHASE_8_STEP_1_SCIENTIFIC_VALIDATION_AUDIT.md)
- **Scientific Defense Guide**: [`SIH_SCIENTIFIC_DEFENSE_GUIDE.md`](file:///SIH_SCIENTIFIC_DEFENSE_GUIDE.md)
- **System Integration Report**: [`outputs/phase_7/PHASE_7_STEP_4_FINAL_END_TO_END_VALIDATION_REPORT.md`](file:///outputs/phase_7/PHASE_7_STEP_4_FINAL_END_TO_END_VALIDATION_REPORT.md)
- **Model Handoff Guide**: [`outputs/phase_5_ml_handoff/ML_INFERENCE_README.md`](file:///outputs/phase_5_ml_handoff/ML_INFERENCE_README.md)
- **API Contract Specification**: [`outputs/phase_5c_api/ML_API_CONTRACT.md`](file:///outputs/phase_5c_api/ML_API_CONTRACT.md)
- **Dashboard Data Dictionary**: [`outputs/phase_5b_dashboard/DASHBOARD_DATA_DICTIONARY.md`](file:///outputs/phase_5b_dashboard/DASHBOARD_DATA_DICTIONARY.md)
