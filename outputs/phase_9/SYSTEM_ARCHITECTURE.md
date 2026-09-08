# Industrial Fire Detection & Classification System
## High-Level Architecture & Dataflow Specification

This document details the multi-tiered architecture of the **Industrial Fire Detection & Classification System** designed for the **Smart India Hackathon (SIH) 2026**.

---

## 1. High-Level System Architecture Diagram

```mermaid
graph TD
    subgraph SENSORS["1. Multi-Source Ingestion & Spatial Sensors"]
        F1["NASA FIRMS (VIIRS 375m)<br/>Thermal Radiance, FRP, Brightness"]
        F2["ESA WorldCover (10m)<br/>Land Cover Taxonomy (Built-up, Cropland, etc.)"]
        F3["OpenStreetMap (OSM Overpass)<br/>Infrastructure, Substations, Industrial Polygons"]
        F4["Copernicus Sentinel-2 MSI (CDSE)<br/>10-20m VNIR/SWIR Optical Bands, dNBR, dNDVI"]
    end

    subgraph PIPELINE["2. Spatial-Temporal Feature Engineering (36 Features)"]
        FE1["Thermal & Temporal Signatures<br/>(FRP, Brightness, Active Days, Persistence Flag)"]
        FE2["Land Use & Environmental Context<br/>(WorldCover Class, Cropland/Forest Masks)"]
        FE3["Proximity & Infrastructure Metrics<br/>(Distance to Industrial Facility, Distance to Substation)"]
        FE4["Optical Burn Severity Deltas<br/>(dNBR, Pre/Post NDVI Change, Observation Flags)"]
        FE_MERGE["36-Feature Normalized Vector<br/>(EventFeatures Schema, Zero Target Leakage)"]
        FE1 --> FE_MERGE
        FE2 --> FE_MERGE
        FE3 --> FE_MERGE
        FE4 --> FE_MERGE
    end

    F1 --> FE1
    F2 --> FE2
    F3 --> FE3
    F4 --> FE4

    subgraph ML_CORE["3. Machine Learning Inference Engine"]
        PREP["ColumnTransformer<br/>• SimpleImputer (Median)<br/>• OneHotEncoder (Categoricals)"]
        MODEL["RandomForestClassifier<br/>• 100 Estimators, Max Depth 6<br/>• Class Weights: Balanced<br/>• SHA-256: 5909bb54...7998"]
        GT["Independent Ground Truth<br/>• 76 Supervised Controls<br/>• 24 REVIEW_REQUIRED Held-out"]
        PREP --> MODEL
    end

    FE_MERGE --> PREP

    subgraph BACKEND["4. ML Inference Service (FastAPI :8000)"]
        SEC["Security Dependency<br/>X-API-Key Header Validation"]
        EP_HEALTH["GET /api/v1/health<br/>Model Liveness & Metadata"]
        EP_PREDICT["POST /api/v1/predict<br/>36-Feature Live Inference"]
        SEC --> EP_PREDICT
        MODEL --> EP_PREDICT
    end

    subgraph PROXY["5. Security & Reverse Proxy Layer (Vite Node.js)"]
        DEV_PROXY["Development Proxy (:5173)<br/>Injects X-API-Key Server-Side"]
        PREV_PROXY["Preview Proxy (:4173)<br/>Injects X-API-Key Server-Side"]
    end

    EP_PREDICT <--> DEV_PROXY
    EP_PREDICT <--> PREV_PROXY
    EP_HEALTH <--> DEV_PROXY
    EP_HEALTH <--> PREV_PROXY

    subgraph FRONTEND["6. Interactive Triage Dashboard (React 19 + TypeScript + Leaflet)"]
        MAP["Leaflet GIS Map<br/>• 633 Candidate Events<br/>• Color-coded 3 ML Classes<br/>• Clustered Markers"]
        FILTERS["Multi-Facet Filter Panel<br/>• ML Class, Confidence<br/>• FRP Slider, Persistence Flag"]
        DRAWER["Event Detail Drawer (5 Evidence Tiers)<br/>• NASA FIRMS Radiance<br/>• Multi-day Persistence<br/>• ESA WorldCover Context<br/>• OSM Proximity & Facility<br/>• Sentinel-2 Optical dNBR"]
        RE_PREDICT["Live Re-Prediction Card<br/>• Real-time Feature Dispatch<br/>• API Latency Counter<br/>• Baseline Parity Verification"]
        KPIS["Summary KPI Bar<br/>• Total, Industrial, Agri, Natural"]
    end

    DEV_PROXY <--> RE_PREDICT
    PREV_PROXY <--> RE_PREDICT
    MAP <--> DRAWER
    FILTERS <--> MAP
    FILTERS <--> KPIS
    DRAWER --> RE_PREDICT
```

---

## 2. Component Tier Breakdown

### Tier 1: Multi-Sensor & Spatial Ingestion
1. **NASA FIRMS (VIIRS 375 m):** Detects radiometric thermal anomalies at 375 m resolution from Suomi-NPP and NOAA-20/21 satellites. Provides Fire Radiative Power (FRP), brightness temperature, and acquisition timestamp.
2. **ESA WorldCover (10 m):** Global land cover dataset providing baseline ecological categorization (Tree cover, Shrubland, Grassland, Cropland, Built-up, Bare vegetation, Water bodies).
3. **OpenStreetMap (OSM Overpass API / Cache):** Extracts surrounding infrastructure geometries within a 2,000 m radius, calculating proximity to nearest industrial facilities, factories, power substations, and mineral extraction quarries.
4. **Copernicus Sentinel-2 MSI (CDSE API):** Multispectral Instrument providing 10 m to 20 m optical reflectance. Measures pre-fire and post-fire surface burn severity ($\text{dNBR}$) and vegetation health ($\Delta\text{NDVI}$).

### Tier 2: 36-Feature Pipeline
The 36 features capture:
- **Thermal Intensity:** `frp`, `brightness`, `brightness_difference`, `bright_t31`.
- **Temporal Persistence:** `grid_detection_count`, `grid_active_days`, `persistent_location_flag`, `is_stubble_burning_season`.
- **Spatial / Local Context:** `grid_brightness_mean`, `frp_zscore_local`, `brightness_zscore_local`.
- **Land Cover:** One-hot encoded WorldCover classes (`worldcover_Built-up`, `worldcover_Cropland`, `worldcover_Tree cover`, etc.).
- **Infrastructure Proximity:** `distance_to_facility_m`, `near_industrial_500m`, `near_industrial_1000m`, `nearest_facility_category`.
- **Optical Surface Change:** `s2_dnbr_mean`, `s2_pre_ndvi_mean`, `s2_post_ndvi_mean`, `s2_change_status`.

### Tier 3: Machine Learning Inference Core
- **Pipeline:** Serialized `sklearn.pipeline.Pipeline` (`final_model.joblib`).
- **Preprocessor:** `ColumnTransformer` with median imputation for missing numericals and one-hot encoding for categoricals.
- **Classifier:** `RandomForestClassifier(n_estimators=100, max_depth=6, class_weight='balanced', random_state=42)`.
- **Target Classes:**
  1. `Agricultural Burning`
  2. `Industrial Thermal Activity`
  3. `Natural / Wildfire / Other`
- **Integrity Digest:** SHA-256 `5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798`.

### Tier 4: FastAPI Backend Service
- **Framework:** FastAPI with Uvicorn ASGI server running on `127.0.0.1:8000`.
- **Endpoints:**
  - `GET /api/v1/health`: Checks model loading state, returns feature count and SHA-256.
  - `POST /api/v1/predict`: Accepts 36 features, runs inference in $\le 25\text{ ms}$, returns predicted class and probability distribution.
- **Security:** Requires `X-API-Key` header validated via dependency injection (`src/api/security.py`).

### Tier 5: Reverse Proxy & Security Perimeter
- Configured in `frontend/vite.config.ts` for both development (`:5173`) and production preview (`:4173`).
- Injects `X-API-Key` strictly on the Node.js server side.
- Zero secrets or API keys are bundled into client-side JavaScript or exposed in browser network requests.

### Tier 6: Interactive GIS Triage Dashboard
- **Framework:** React 19 + TypeScript + Leaflet + Vanilla CSS.
- **Data:** Master 633-event dataset (`dashboard_events_633.csv`, SHA-256: `f74d1a96...93eb`).
- **Key Modules:**
  - `FireMap`: Leaflet map with custom marker styling according to ML class.
  - `FilterPanel`: Multi-dimensional filtering by class, confidence, FRP, and persistence.
  - `EventDetailDrawer`: Slide-over drawer presenting 5 evidence tiers and scientific disclaimers.
  - `LivePredictionCard`: Re-runs prediction against the live FastAPI service on demand.
  - `BackendStatusBadge`: Polls `/api/v1/health` with retry backoff and overlap protection.

---

## 3. End-to-End Live Prediction Flow

```mermaid
sequenceDiagram
    autonumber
    actor Operator as SIH Judge / Operator
    participant UI as React Frontend (Browser)
    participant Proxy as Vite Dev/Preview Proxy
    participant API as FastAPI Backend (:8000)
    participant Model as RandomForest Pipeline

    Operator->>UI: Selects Event (e.g. JSW Steel FIRMS_TN_0008)
    UI->>UI: Opens EventDetailDrawer with static baseline evidence
    Operator->>UI: Clicks "Re-run Live Prediction"
    UI->>UI: Loads 36 features from lookup table
    UI->>Proxy: POST /api/v1/predict (JSON payload, No API Key)
    Note over Proxy: Server-side Node.js intercepts request<br/>Injects X-API-Key header
    Proxy->>API: POST /api/v1/predict (with X-API-Key)
    API->>API: Validates API Key & validates 36 features
    API->>Model: predict_proba(feature_array)
    Model-->>API: Probabilities: [0.0031, 0.9969, 0.0000]
    API-->>Proxy: HTTP 200 JSON (predicted_class, probabilities, execution_time_ms)
    Proxy-->>UI: Forwards HTTP 200 response
    UI->>UI: Renders "Live API Result", latency (~18ms), Matches Baseline: Yes
```
