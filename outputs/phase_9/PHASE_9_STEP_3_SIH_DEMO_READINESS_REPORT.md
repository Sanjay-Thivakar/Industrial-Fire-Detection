# Phase 9 — Step 3: SIH Demonstration & Presentation Readiness Audit Report

**Document:** `outputs/phase_9/PHASE_9_STEP_3_SIH_DEMO_READINESS_REPORT.md`  
**Phase:** 9 — Final Submission & Demonstration Readiness  
**Step:** 3 — SIH Demonstration & Presentation Readiness Audit  
**Date:** September 7, 2026  
**Status:** COMPLETE (READ-ONLY AUDIT & DEMO PLAN)  
**Verdict:** **READY FOR LIVE DEMONSTRATION**

---

## 1. Executive Summary

This report evaluates the **Industrial Fire Detection & Classification System** for technical robustness, presentation clarity, and scientific defensibility during the upcoming **Smart India Hackathon (SIH) 2026** jury presentation.

The system is evaluated against real-time demonstration constraints, judge technical cross-examination, failure contingency modes, and live API re-prediction workflows.

**Key Findings:**
1. **End-to-End Operation:** Both development (`:5173`) and production preview (`:4173`) frontend modes communicate seamlessly with the FastAPI backend (`:8000`) via secure, server-side proxy header injection.
2. **Deterministic Baseline:** The 633-event static dashboard data and 36-feature lookup provide an instant, zero-latency presentation experience even if external internet or live backend is interrupted.
3. **Live Re-Prediction:** The live API integration path reliably exercises the exact 36-feature vector against the serialized scikit-learn Random Forest pipeline (`5909bb54...7998`) with verified contract parity.
4. **Scientific Honesty:** The documentation and presentation guidelines strictly forbid overclaiming accuracy (e.g., prohibiting claims of "93.33% accuracy"), clearly distinguishing sensor anomaly detection from ML statistical classification and optical change context.

---

## 2. Application Startup Audit

The exact commands and environment requirements to start the application are verified below:

### A. ML Inference Backend (FastAPI + Uvicorn)
- **Working Directory:** Repository root (`c:\Users\divas\Desktop\Industrial-Fire-Detection`)
- **Environment:** Dedicated Python 3.11 virtual environment (`.venv`)
- **Command:**
  ```powershell
  .venv\Scripts\activate
  uvicorn src.api.main:app --host 127.0.0.1 --port 8000
  ```
- **Configuration & Environment Variables:**
  - `ML_API_KEY`: Read from `.env` or system environment (defaults to development key if unset for local testing).
  - `MODEL_PATH`: Points to `outputs/phase_5_ml_handoff/final_model.joblib`.
  - `LOG_LEVEL`: Default `INFO`.
- **Model Loading:** The serialized pipeline (`sklearn.pipeline.Pipeline`) loads into memory on startup lifecycle hook (`@app.on_event("startup")`), verifying 36 input features and 3 output classes.
- **Verification Endpoint:**
  - Liveness: `GET http://127.0.0.1:8000/api/v1/health` $\rightarrow$ `{"status": "online", "model_loaded": true, "model_version": "1.0.0"}`
  - Interactive OpenAPI Swagger: `http://127.0.0.1:8000/docs`

### B. Frontend Development Mode
- **Working Directory:** `frontend/`
- **Dependencies:** Already installed in `frontend/node_modules/` (Node.js 20+ / 22+)
- **Command:**
  ```powershell
  cd frontend
  npm run dev
  ```
- **Expected URL:** `http://127.0.0.1:5173/`
- **Vite Proxy Behavior:** Development proxy forwards all `/api/*` requests to `http://127.0.0.1:8000/api/*` and automatically injects the `X-API-Key` header on the Node.js dev server side.

### C. Frontend Production Preview Mode
- **Working Directory:** `frontend/`
- **Build & Preview Commands:**
  ```powershell
  cd frontend
  npm run build
  npm run preview
  ```
- **Expected URL:** `http://127.0.0.1:4173/`
- **Preview Proxy Behavior:** Configured in `frontend/vite.config.ts` under `preview.proxy`, matching development proxy routing and header injection identically.

---

## 3. Dashboard Demonstration Audit

The production frontend implementation was audited across all presentation dimensions:

| Component / Feature | Implementation Location | Demo Verification Status | Live Demonstration Capability |
|---|---|:---:|---|
| **633 Dashboard Events** | `frontend/src/services/dataLoader.ts` | **PASS** | Complete Tamil Nadu 2024 candidate cohort parsed and rendered. |
| **Interactive GIS Map** | `frontend/src/components/map/FireMap.tsx` | **PASS** | Leaflet map with smooth panning, clustering, zoom, and tile rendering. |
| **Three Official ML Classes** | `frontend/src/types/dashboard.ts` | **PASS** | Color-coded markers: Red (Industrial), Amber (Agri), Green (Natural). |
| **Interactive Map Legend** | `frontend/src/components/map/MapLegend.tsx` | **PASS** | Compact overlay displaying 3 ML classes and sensor confidence shapes. |
| **Multi-Facet Filters** | `frontend/src/components/filters/FilterPanel.tsx` | **PASS** | Filters by ML class, confidence, FRP range, persistence, land cover. |
| **KPI / Summary Bar** | `frontend/src/components/layout/SummaryBar.tsx` | **PASS** | Dynamic counters updating instantly with active filter subsets. |
| **Event Selection** | `frontend/src/App.tsx` | **PASS** | Clicking marker or Quick Pick opens drawer and highlights marker. |
| **Event Detail Drawer** | `frontend/src/components/events/EventDetailDrawer.tsx` | **PASS** | 460px right-side slide-over panel with deep evidence hierarchy. |
| **ML Probability Breakdown** | `frontend/src/components/events/ProbabilityBars.tsx` | **PASS** | Three horizontal percentage bars with color-coordinated styling. |
| **Confidence Distinction** | `frontend/src/components/events/EventDetailDrawer.tsx` | **PASS** | Strictly displays ML confidence and FIRMS sensor confidence separately. |
| **OSM Context** | `frontend/src/components/events/DetailSection.tsx` | **PASS** | Nearest facility, category, distance, and industrial coverage status. |
| **WorldCover Context** | `frontend/src/components/events/DetailSection.tsx` | **PASS** | Land-cover classification (Built-up, Cropland, Tree cover, etc.). |
| **Sentinel-2 Optical Context** | `frontend/src/components/events/DetailSection.tsx` | **PASS** | Pre/Post image dates, dNBR surface burn metric, cloud/masked status. |
| **Human Validation Details** | `frontend/src/components/events/DetailSection.tsx` | **PASS** | Displays ground truth when available; displays "Not human validated" otherwise. |
| **Live FastAPI Re-Prediction** | `frontend/src/components/events/LivePredictionCard.tsx` | **PASS** | Dispatches feature vector to `/api/v1/predict` and displays latency. |

### Potential Presentation Pitfalls & UI Behaviors:
1. **Drawer Compression on Small Displays:** At $<1280\text{px}$, responsive CSS automatically reduces drawer width from 460px to 380px and sidebar from 290px to 240px. Use standard $1920\times1080$ or $1366\times768$ display resolution for best presentation.
2. **Filter & Selection Coordination:** Selecting a Quick Pick automatically clears conflicting filters if the target event would otherwise be filtered out.

---

## 4. Demo Event Selection Audit

The four pre-configured Demo Quick Picks (`frontend/src/utils/quickPickEvents.ts`) were audited against the authoritative dataset:

```
+---------------------------------------------------------------------------------------------------+
| Event ID      | Name / Site               | Predicted Class            | Max Prob | ML Conf | FRP   |
+---------------+---------------------------+----------------------------+----------+---------+-------+
| FIRMS_TN_0000 | Salem Steel Plant (SAIL)  | Industrial Thermal Activity| 50.31%   | MEDIUM  | 1.16  |
| FIRMS_TN_0008 | JSW Steel Plant (Mecheri) | Industrial Thermal Activity| 99.69%   | HIGH    | 1.06  |
| FIRMS_TN_0001 | Ramanathapuram Cropland   | Agricultural Burning       | 69.51%   | MEDIUM  | 5.15  |
| FIRMS_TN_0004 | Quarry / Mining Proximity | Agricultural Burning       | 69.17%   | MEDIUM  | 4.01  |
+---------------------------------------------------------------------------------------------------+
```

### Detailed Event Profiles for Presentation:

#### 1. `FIRMS_TN_0000` — Salem Steel Plant (SAIL)
- **Location:** Lat: 11.65394, Lon: 78.02792 (Salem District)
- **Detection:** Night observation (19:40 UTC), FRP: 1.16 MW, Brightness: 311.1 K.
- **Physical Context:** Built-up land cover (WorldCover 50); OSM identifies SAIL Substation at 328 m.
- **ML Prediction:** Industrial Thermal Activity (Probability: 50.31% Industrial, 43.31% Agri, 6.39% Natural).
- **Presentation Value:** Demonstrates how infrastructure context flags industrial origin even with modest FRP and single-day satellite trigger.

#### 2. `FIRMS_TN_0008` — JSW Steel Plant (Mecheri)
- **Location:** Lat: 11.81736, Lon: 77.91756 (Salem / Mecheri industrial corridor)
- **Detection:** Night observation (20:25 UTC), FRP: 1.06 MW.
- **Physical Context:** 20 active hotspot days (`persistent_location_flag = 1`), Built-up land cover, Electrical Substation at 215 m.
- **ML Prediction:** Industrial Thermal Activity (Probability: **99.69% Industrial**, 0.31% Agri, 0.00% Natural).
- **Presentation Value:** The flagship industrial demo event. Demonstrates how temporal spatial recurrence (20 days) + industrial zone drives high model certainty.

#### 3. `FIRMS_TN_0001` — Ramanathapuram Cropland (Held-Out Human Review)
- **Location:** Lat: 9.29417, Lon: 79.06924 (Southern Coastal agricultural belt)
- **Detection:** Daytime observation (08:26 UTC), FRP: 5.15 MW.
- **Physical Context:** Tree cover / agricultural interface; power plant at 2.8 km (outside immediate industrial threshold).
- **ML Prediction:** Agricultural Burning (69.51% Agri, 16.02% Industrial, 14.47% Natural).
- **Human Ground Truth:** **`REVIEW_REQUIRED`** (Held out from supervised training).
- **Presentation Value:** Demonstrates scientific integrity. Shows judges that ambiguous events were strictly excluded from model training rather than forced into artificial labels.

#### 4. `FIRMS_TN_0004` — Mining & Quarry Proximity (Optical & OSM Fallback)
- **Location:** Lat: 13.20969, Lon: 79.91416 (Tiruvallur District)
- **Detection:** Daytime observation (07:50 UTC), FRP: 4.01 MW.
- **Physical Context:** Cropland (WorldCover 40); OSM status is `FAILED_TILE` (graceful fallback); Sentinel-2 optical imagery is valid with post-fire change metric $\text{dNBR} = +0.023$.
- **ML Prediction:** Agricultural Burning (69.17% Agri, 0.00% Industrial, 30.83% Natural).
- **Human Ground Truth:** Verified **Agricultural Burning** (Unambiguous).
- **Presentation Value:** Demonstrates multi-sensor fusion: despite OSM tile server failure, WorldCover + Sentinel-2 optical change + daytime thermal signature correctly guide classification.

---

## 5. Live API Demonstration Audit

The complete live re-prediction path was verified end-to-end:

```
[Browser UI: "Run Live Re-Prediction"]
                 │
                 ▼
  [Client Service: apiClient.ts]
  POST /api/v1/predict (Feature payload: 36 features, No API Key in client code)
                 │
                 ▼
  [Vite Reverse Proxy: :5173 / :4173]
  Intercepts /api/v1/predict -> Injects 'X-API-Key: sih_dev_secret_key_2026'
                 │
                 ▼
  [FastAPI Backend: src/api/main.py (:8000)]
  Security Dependency -> Validates X-API-Key -> Deserializes EventFeatures
                 │
                 ▼
  [Model Inference Pipeline: src/models/predict.py]
  ColumnTransformer -> RandomForestClassifier.predict_proba()
                 │
                 ▼
  [HTTP 200 JSON Response: PredictionResponse]
  predicted_class, probabilities, ml_confidence, execution_time_ms
                 │
                 ▼
  [Browser UI: LivePredictionCard.tsx]
  Displays "Live API Result", latency (~12-25 ms), "Matches Baseline: Yes"
```

### Verification Findings:
1. **Feature Integrity:** All 36 features are loaded directly from `event_features_36_lookup.json` for the selected event and transmitted to the API.
2. **Zero Client Secrets:** The browser network request never contains `X-API-Key` or secret tokens. Header injection is entirely server-side in Node.js.
3. **Contract Parity:** Re-predicting `FIRMS_TN_0008` produces identical probabilities (`[0.0031, 0.9969, 0.0]`) to the baseline batch inference, verifying 100% mathematical consistency.
4. **Recommended Event for Live Demonstration:** `FIRMS_TN_0008` (JSW Steel) or `FIRMS_TN_0000` (SAIL).

---

## 6. Scientific Storyline Audit

The demonstration must adhere strictly to the following epistemological framework:

```
+----------------------------------------------------------------------------------------------------+
| Layer / Sensor       | Physical Measurement              | Scientific Role in System               |
+----------------------+-----------------------------------+-----------------------------------------+
| NASA VIIRS (FIRMS)   | 375 m Mid-IR / Thermal Radiance   | Where & when thermal anomalies occurred |
| OpenStreetMap (OSM)  | Vector Infrastructure Polygons    | Contextual proximity (NOT causality)    |
| ESA WorldCover       | 10 m Optical Land Cover Taxonomy  | Baseline ecological/surface setting     |
| Copernicus S2 MSI    | 10-20 m VNIR/SWIR Reflectance     | Optical surface change (NOT thermal)    |
| Random Forest Model  | Multi-Source Feature Synthesis    | Algorithmic probability estimation      |
| Human Ground Truth   | Independent Expert Imagery Audit  | 76 supervised controls (Zero leakage)   |
+----------------------------------------------------------------------------------------------------+
```

### Core Storyline Principles:
- **NASA FIRMS** identifies thermal radiance anomalies; it does not know if heat comes from a boiler, a flare stack, crop stubble, or dry scrub.
- **Sentinel-2** is an optical sensor, not a thermal camera. It detects surface burn scars and vegetation loss. Absence of imagery (due to clouds or 5-day revisit) does **not** mean absence of fire.
- **OpenStreetMap** provides spatial context. Being 200 m from a substation does not prove the fire came from the substation; it provides Bayesian evidence for the classifier.
- **Machine Learning** is an empirical classification tool trained on audited reference cases.
- **Ground Truth** is independently maintained and never overwritten by model outputs.

---

## 7. Metrics Presentation Audit

The reported metrics must be stated with mathematical precision:

### Authoritative Model Performance Metrics (5-Fold Stratified CV, $n=76$):
- **Out-of-Fold Macro F1:** **0.7772** (Cross-validation mean: $0.7594 \pm 0.1312$)
- **Out-of-Fold Balanced Accuracy:** **0.7693** (Cross-validation mean: $0.7733 \pm 0.1183$)
- **Class-Specific Breakdown:**
  - **Industrial Thermal Activity:** Recall = **93.33%** (14/15), Precision = **87.50%** (14/16), F1 = **0.9032**
  - **Agricultural Burning:** Recall = **92.00%** (46/50), Precision = **88.46%** (46/52), F1 = **0.9020**
  - **Natural / Wildfire / Other:** Recall = **45.45%** (5/11), Precision = **62.50%** (5/8), F1 = **0.5263**

> [!IMPORTANT]
> **CRITICAL RULE FOR PRESENTATION:**
> The figure **93.33%** is the **Industrial Thermal Activity Recall** (14 out of 15 industrial events correctly identified).
> It is **NOT** the overall model accuracy. Overall Balanced Accuracy is **76.93%**, and Macro F1 is **0.7772**.

---

## 8. Required Judge Disclosures

The presentation must proactively and transparently disclose the following technical boundaries:

1. **Candidate Pool Pre-Selection Bias:**
   The 633 events do not represent all fires in Tamil Nadu; they represent a filtered candidate pool geographically enriched near industrial corridors and candidate sites. The 41.2% industrial prediction share reflects this candidate selection, not statewide natural fire distribution.
2. **Supervised Sample Size ($n=76$):**
   The supervised training cohort contains 76 rigorously validated events. 24 ambiguous events were held out under `REVIEW_REQUIRED`. The system does not pretend to have thousands of human ground truth labels.
3. **Class Imbalance:**
   The training set has 50 Agricultural, 15 Industrial, and 11 Natural events. Balanced class weighting (`class_weight='balanced'`) was employed to prevent majority class collapse.
4. **Uncalibrated Model Probabilities:**
   Random Forest output probabilities represent decision tree voting fractions, not calibrated Bayesian posterior probabilities.
5. **Persistent Industrial Thermal Sources:**
   High recurrence (e.g., JSW Steel, 20 active days) denotes persistent industrial thermal activity (furnaces, flares, cooling operations), which are grouped under the industrial class for the SIH problem statement, but are distinct from catastrophic industrial fires.
6. **OSM Retrieval Failure:**
   `FAILED_TILE` indicates an Overpass API or caching timeout for that geographic cell; it does not mean no industrial facility exists.

---

## 9. Differentiation from NASA FIRMS

Judges frequently ask: *"Why do we need your platform if NASA FIRMS already detects fires?"*

### Clear Differentiation Summary:
```
+-----------------------------------+-----------------------------------+
| NASA FIRMS Alone                  | Our Integrated System             |
+-----------------------------------+-----------------------------------+
| Point coordinates + date/time     | Exact facility & infrastructure   |
| Raw radiance & FRP (MW)           | 10 m ESA WorldCover context       |
| Sensor confidence (l / n / h)     | Multi-day temporal persistence    |
| No fire type or origin            | Sentinel-2 optical burn change    |
| No facility proximity             | ML classification (3 classes)     |
| Raw CSV / static map              | Interactive triage GIS dashboard  |
| No ground truth evaluation        | Human-audited benchmark cohort    |
| Alerts everything identically     | Prioritizes high-risk industrial  |
+-----------------------------------+-----------------------------------+
```

---

## 10. Frequently Asked Questions & Defensible Answers

### Q1: Why can't NASA FIRMS alone identify industrial fires?
**Answer:** NASA FIRMS detects mid-infrared thermal radiation anomalies using 375 m VIIRS pixels. It detects the presence of heat, but has zero knowledge of land use, facility proximity, or historical recurrence. A sugar mill boiler flare, a stubble fire in an adjacent field, and a forest blaze register identically as thermal pixels.

### Q2: Why did you choose VIIRS over MODIS?
**Answer:** VIIRS (Suomi-NPP and NOAA-20/21) provides 375 m spatial resolution in the I-bands compared to 1 km for MODIS. For industrial sites (smelters, refineries, power plants), 375 m resolution dramatically reduces spatial blurring, enabling accurate correlation with localized facility footprints.

### Q3: Why use Sentinel-2 if it isn't a thermal sensor?
**Answer:** Sentinel-2 provides 10 m to 20 m multispectral optical reflectance in the visible, near-infrared (VNIR), and shortwave-infrared (SWIR). It measures pre- and post-event surface burn severity ($\text{dNBR}$) and vegetation index drop ($\Delta\text{NDVI}$). While FIRMS detects the active thermal pulse, Sentinel-2 confirms physical surface change or structural damage.

### Q4: Why use OpenStreetMap (OSM)?
**Answer:** OSM provides global, community-verified infrastructure geometry (industrial plants, power substations, chemical storage, pipelines). We compute exact distance to the nearest industrial facility and evaluate hierarchical industrial relevance within 500 m, 1,000 m, and 2,000 m radii.

### Q5: Why is the model only three classes?
**Answer:** The three classes—*Agricultural Burning*, *Industrial Thermal Activity*, and *Natural / Wildfire / Other*—reflect the operational decision boundaries required by emergency and environmental response agencies. A finer taxonomy (e.g., splitting petrochemical vs metallurgical) was rejected because it would lack sufficient human ground-truth support ($n=76$) and create severe label noise.

### Q6: Why isn't your model accuracy 93.33%?
**Answer:** 93.33% is the **Recall** specifically for the *Industrial Thermal Activity* class (14 out of 15 true industrial events detected). In an operational fire triage system, missing an industrial event (false negative) is catastrophic, so the model was tuned for high industrial recall. The overall Balanced Accuracy is **76.93%**, and Macro F1 is **0.7772**.

### Q7: How did you obtain ground truth without data leakage?
**Answer:** An independent human validation protocol audited 100 candidate events using high-resolution Google Earth imagery, historical news reports, and Tamil Nadu industrial registry data. Exactly 76 events were verified unambiguously, while 24 ambiguous events were labeled `REVIEW_REQUIRED` and strictly excluded from model training. Model inputs contain zero human validation columns.

### Q8: How did you prevent data leakage in feature engineering?
**Answer:** All spatial aggregations and feature transformations were computed strictly within cross-validation folds using scikit-learn `Pipeline` and `ColumnTransformer`. No target labels, validation statuses, or future temporal observations were accessible to the feature matrix.

### Q9: Why are Sentinel-2 observations missing for many events?
**Answer:** Tamil Nadu has a 40.1% average cloud cover rate, and Sentinel-2 has a 5-day revisit cycle. When cloud cover obscures the target or pixels are masked by the Scene Classification Layer (SCL), optical data is unavailable. The pipeline handles this gracefully without hallucinating values.

### Q10: What is the difference between ML confidence and FIRMS confidence?
**Answer:** FIRMS confidence (`l`, `n`, `h`) is the satellite instrument's internal metric representing the radiometric quality and signal-to-noise ratio of the thermal detection. ML confidence (`LOW`, `MEDIUM`, `HIGH`) represents the Random Forest ensemble margin between the top predicted class and competing classes.

### Q11: Can the model guarantee an event is an industrial fire?
**Answer:** No. Machine learning outputs are probabilistic estimates based on available features, not ground truth. The system explicitly displays a scientific disclaimer stating that predictions are decision-support aids, not physical guarantees.

### Q12: What happens when OSM data retrieval fails?
**Answer:** If the Overpass API times out, the system marks the status as `FAILED_TILE`. The feature extractor assigns standardized fallback values (imputed median distance) rather than assuming zero industrial presence, and the event drawer explicitly alerts the operator.

### Q13: What is the biggest limitation of the current model?
**Answer:** The primary limitation is the modest size of the supervised training cohort ($n=76$), which limits the model's ability to distinguish subtle natural wildfires in scrubland from agricultural burn events (Natural F1 = 0.5263).

### Q14: How would you improve the system with more time and data?
**Answer:** 1) Expand human validation across other industrial states (e.g., Gujarat, Maharashtra); 2) Incorporate geostationary INSAT-3D/3DR 15-minute thermal observations; 3) Integrate meteorological wind and humidity vectors from ECMWF ERA5.

### Q15: How is this different from simply using FIRMS + Google Maps?
**Answer:** Manually cross-referencing FIRMS coordinates against Google Maps takes 5–10 minutes per event and relies on subjective operator guesswork. Our system automates multi-sensor feature extraction in milliseconds, applies an audited machine learning model, computes quantitative burn metrics, and surfaces structured risk indicators instantly.

### Q16: Can this system operate in near real-time (NRT)?
**Answer:** Yes. The FastAPI backend processes a single 36-feature payload in under 25 milliseconds. When paired with the NASA FIRMS NRT API (which delivers thermal detections within 1 to 3 hours of satellite overpass), automated classification can run continuously.

### Q17: What happens when a completely new event is detected?
**Answer:** The coordinates and timestamp are passed to the automated feature extractor, which queries the local OSM spatial index, extracts WorldCover land cover, aggregates localized FIRMS history, and dispatches the 36-feature vector to `/api/v1/predict` for instant classification.

### Q18: What are the known failure modes of your model?
**Answer:** In our out-of-fold validation, we identified 1 Industrial False Negative (`FIRMS_TN_0176`, low 4.52 MW thermal pulse in dense tree cover with no historical persistence) and 2 Industrial False Positives (`FIRMS_TN_0093` and `FIRMS_TN_0258`, multi-day agricultural and forest fires that falsely triggered the spatial persistence flag).

---

## 11. 3–5 Minute Live Demonstration Script

```
================================================================================
TIME        SECTION                     ACTIONS & TALKING POINTS
================================================================================
0:00 - 0:30 Problem Statement           • "Every day, NASA satellites detect hundreds of thermal anomalies across India.
                                           However, disaster managers cannot distinguish dangerous factory fires from routine
                                           crop stubble burning without manual investigation."
                                         • "We built an end-to-end multi-sensor system that classifies satellite thermal
                                           events into Industrial, Agricultural, and Natural categories in real time."

0:30 - 1:15 Statewide GIS Dashboard     • Display dashboard at http://127.0.0.1:5173/ showing 633 Tamil Nadu events.
                                         • Highlight color coding: Red (Industrial), Amber (Agri), Green (Natural).
                                         • Show Summary KPI bar (261 Industrial, 287 Agricultural, 85 Natural).
                                         • Explain: "These 633 events represent our 2024 Tamil Nadu candidate cohort."

1:15 - 2:00 Interactive Filtering       • Click Filter Panel: Filter by "Industrial Thermal Activity" + "High ML Confidence".
                                         • Observe map updating dynamically: clustering along Chennai, Salem, Coimbatore corridors.
                                         • Reset filters to restore full dataset.

2:00 - 2:45 Deep Evidence Inspection    • Click Demo Quick Pick: FIRMS_TN_0008 (JSW Steel Plant, Mecheri).
                                         • Drawer slides open.
                                         • Walk judges through the 5 evidence tiers:
                                           1. Sensor: 1.06 MW FRP, night detection.
                                           2. Persistence: 20 active days (strong recurrent signature).
                                           3. WorldCover: Class 50 (Built-up industrial footprint).
                                           4. OSM: Substation at 215 m.
                                           5. Sentinel-2: Cloud masked status honestly disclosed.

2:45 - 3:30 Live API Re-Prediction      • Scroll down in drawer to "Live Model Inference" card.
                                         • Click "Re-run Live Prediction".
                                         • Watch live FastAPI roundtrip execute in ~18 ms.
                                         • Point to "Matches Baseline: Yes" and latency counter.
                                         • Explain: "The browser extracted 36 features and hit our FastAPI backend via secure
                                           reverse proxy with zero client-side secret exposure."

3:30 - 4:15 Probability & Confidence    • Highlight probability bars: 99.69% Industrial, 0.31% Agricultural, 0.00% Natural.
                                         • Explain confidence distinction:
                                           "Notice that FIRMS sensor confidence is 'Nominal' (n), while ML confidence is 'HIGH'.
                                           Our system never confuses satellite radiometric quality with model certainty."

4:15 - 5:00 Validation, Limits & Close  • Click Quick Pick FIRMS_TN_0001 (Ramanathapuram Cropland).
                                         • Show Human Validation section: status is "REVIEW_REQUIRED".
                                         • Explain: "We maintain 76 audited ground truth controls and strictly excluded 24
                                           ambiguous cases. Our Industrial Recall is 93.33%, Macro F1 is 0.7772."
                                         • Close: "By transforming raw thermal pixels into verified contextual intelligence,
                                           our system empowers emergency responders to act before disaster spreads."
================================================================================
```

---

## 12. What NOT to Claim

| Prohibited Statement (DO NOT SAY) | Why It Is Scientifically Flawed | Approved Replacement Statement |
|---|---|---|
| *"Our model has 93.33% accuracy."* | 93.33% is Industrial Recall on $n=15$. Overall Balanced Accuracy is 76.93%. | *"Our model achieves 93.33% recall on the critical Industrial class, with an overall Balanced Accuracy of 76.93%."* |
| *"The system proves the fire started in the factory."* | OSM proximity shows correlation, not physical causation. | *"OSM provides proximity evidence indicating high likelihood of an industrial thermal source."* |
| *"Sentinel-2 confirms the fire thermally."* | Sentinel-2 is an optical sensor measuring surface reflectance, not heat. | *"Sentinel-2 provides optical evidence of surface burn severity and vegetation change."* |
| *"633 events represent all fires in Tamil Nadu."* | Candidate pool is filtered and geographically pre-selected. | *"The 633 events represent our curated 2024 candidate cohort focused on industrial corridors."* |
| *"The model is 100% certain."* | RF probabilities are voting proportions, not calibrated statistical certainty. | *"The model displays an ensemble voting proportion of 99.7%, categorized as High ML Confidence."* |
| *"Every persistent thermal hotspot is an industrial fire."* | Flares and smelters are normal operations, not uncontrolled blazes. | *"Recurrent thermal hotspots denote persistent industrial thermal activity, including flares and processing heat."* |
| *"FIRMS confidence measures model confidence."* | FIRMS confidence reflects satellite radiometric signal quality. | *"We separate the satellite sensor's radiometric confidence from our machine learning model's confidence."* |

---

## 13. Demo Failure Contingency Plan

```
+---------------------------+-----------------------------------+-----------------------------------------------+
| Failure Scenario          | Immediate Symptom                 | Presentation Fallback Action                  |
+---------------------------+-----------------------------------+-----------------------------------------------+
| Backend Not Running       | Badge shows "Backend: Offline"   | Continue presentation using static baseline   |
|                           | Live prediction button disabled   | data. All 633 events, probabilities, and      |
|                           |                                   | evidence layers are 100% pre-rendered.        |
+---------------------------+-----------------------------------+-----------------------------------------------+
| Live API Call Times Out   | Spinner runs > 5s or error banner | Explain graceful error handling: the UI       |
|                           | "NETWORK_FAILURE" appears         | catches timeouts and preserves static baseline|
|                           |                                   | without crashing. Click "Retry".              |
+---------------------------+-----------------------------------+-----------------------------------------------+
| OSM FAILED_TILE Shown     | Detail drawer says "FAILED_TILE"  | Turn into a strength: "Notice our resilient   |
|                           | for nearest facility              | architecture: when OSM times out, the system  |
|                           |                                   | uses median fallback values and alerts users."|
+---------------------------+-----------------------------------+-----------------------------------------------+
| Sentinel-2 "Unavailable"  | S2 section shows "Unavailable"    | Explain Tamil Nadu's 40.1% cloud cover and    |
|                           | or "MISSING_POST"                 | 5-day revisit cycle. Highlights why multi-    |
|                           |                                   | sensor fusion (FRP + WorldCover) is essential.|
+---------------------------+-----------------------------------+-----------------------------------------------+
| Internet Drops / Offline  | Map background tiles fail to load | Markers, coordinates, filters, and drawer data|
|                           | Leaflet gray grid visible         | continue functioning from cached browser DOM. |
|                           |                                   | Use Quick Picks to switch between events.     |
+---------------------------+-----------------------------------+-----------------------------------------------+
```

---

## 14. Final Presentation Checklist

### Before the Demo (T-15 Minutes):
- [ ] Backend running: `uvicorn src.api.main:app --host 127.0.0.1 --port 8000`
- [ ] Backend health verified: `curl http://127.0.0.1:8000/api/v1/health` $\rightarrow$ `status: online`
- [ ] Frontend running: `cd frontend && npm run dev` (or `npm run preview`)
- [ ] Browser opened to `http://127.0.0.1:5173/` at $1920\times1080$ full screen
- [ ] Header badge confirms `Backend: Online` (green indicator)
- [ ] All 633 events visible on map; KPI bar reads 633 Total, 261 Industrial, 287 Agricultural, 85 Natural
- [ ] Click `FIRMS_TN_0008` Quick Pick to ensure drawer opens smoothly

### During the Demo (0 to 5 Minutes):
- [ ] Start with the core problem: NASA FIRMS cannot distinguish industrial fires from crop burning
- [ ] Show statewide map and explain the 633 candidate cohort
- [ ] Demonstrate multi-facet filters (filter by Industrial + High Confidence)
- [ ] Select `FIRMS_TN_0008` (JSW Steel) via Quick Pick
- [ ] Walk through the 5 evidence layers (FRP, Persistence, WorldCover, OSM, Sentinel-2)
- [ ] Trigger live re-prediction and showcase the ~18 ms response time
- [ ] Highlight the distinction between satellite confidence and model confidence
- [ ] Disclose limitations: 76 supervised controls, candidate pool bias, and 93.33% Industrial Recall

### After the Demo (Q&A):
- [ ] Answer judge questions using the technical answers in Section 10
- [ ] Never overclaim accuracy or claim model predictions are ground truth
- [ ] Emphasize operational emergency dispatch value

---

## 15. Final Verdict

### **READY FOR LIVE DEMONSTRATION**

The system is fully integrated, stable, mathematically verified, and presentation-ready. All features required for an impactful and scientifically rigorous SIH 2026 presentation function without defects or workarounds.

---

## 16. Explicit Modification Audit

- **files modified outside report:** **NO**
- **model modified:** **NO**
- **dataset modified:** **NO**
- **labels modified:** **NO**
- **predictions modified:** **NO**
- **backend modified:** **NO**
- **frontend modified:** **NO**
- **API modified:** **NO**
- **Git operations performed:** **NO**
