# PHASE 6 — STEP 2: FRONTEND ARCHITECTURE & TECHNOLOGY ALIGNMENT
## Industrial Fire Detection System — Web GIS Dashboard Technical Specification

**Date:** 2026-09-07  
**Document Version:** 1.0.0  
**Status:** ARCHITECTURE & SPECIFICATION COMPLETE (Ready for Step 3 Scaffolding)  
**Target Directory:** `frontend/`  
**Core Framework:** React 18 + Vite + TypeScript  
**GIS Engine:** Leaflet + React-Leaflet  
**Backend Reference:** FastAPI ML Inference Service (`src/api/main.py`)  
**Authoritative Dataset:** `outputs/phase_5b_dashboard/dashboard_events_633.csv` (633 rows × 61 columns)  

---

## 1. Technology Stack Specification

The frontend architecture is designed to deliver a high-performance, visually stunning, production-grade GIS dashboard for the Smart India Hackathon jury demonstration.

| Technology | Selected Version / Tool | Role in Architecture | Technical Rationale |
|---|---|---|---|
| **Build Tool & Dev Server** | **Vite 5+** | Project bundler, dev server, and asset pipeline | Sub-second Hot Module Replacement (HMR), native ES modules, zero-overhead static asset serving, built-in development proxy for backend API requests to eliminate CORS. |
| **UI Framework** | **React 18+** | Reactive view layer and component model | Mature component lifecycle, declarative state-driven UI, rich ecosystem for GIS and charting, robust hook-based data flow. |
| **Type System** | **TypeScript 5+** | End-to-end static type enforcement | Guarantees 100% schema fidelity across all 61 dashboard CSV columns and 36 ML API request features. Prevents runtime property mismatches and null pointer errors. |
| **GIS Mapping Engine** | **Leaflet 1.9+** | Core geospatial map rendering engine | Lightweight (<40 KB gzipped), hardware-accelerated tile rendering, battle-tested standard for web GIS. Low memory footprint when rendering 633 points compared to heavy WebGL runtimes. |
| **React GIS Binding** | **React-Leaflet 4+** | React wrapper for Leaflet primitives | Bridges React state with Leaflet's DOM layers (`MapContainer`, `TileLayer`, `CircleMarker`, `Popup`, `Tooltip`). Allows declarative marker synchronization with active filter state. |
| **CSV Parser** | **PapaParse 5.4+** | Browser-side tabular data ingestion | High-speed, streaming CSV parser with Web Worker support. Parses the 420 KB `dashboard_events_633.csv` in < 25 ms with automated type casting. |
| **Iconography** | **Lucide-React** | Modern SVG icons | Crisp, customizable visual cues for fire, industry, agriculture, forest, satellites, sensors, and status badges. |
| **Styling Architecture** | **Vanilla CSS + Modern Design Tokens** | Sleek dark-mode theme, glassmorphism, animations | Pure CSS variables (`index.css`) with curated HSL color palettes (deep slate `#0f172a`, glowing amber `#f59e0b`, crimson `#ef4444`, emerald `#10b981`). Zero CSS-in-JS runtime overhead. |

---

## 2. Frontend Directory Structure

All frontend assets will be housed in a self-contained `frontend/` directory at the repository root, ensuring zero coupling or pollution of existing Python packages:

```
Industrial-Fire-Detection/
├── config/
├── data/
├── outputs/
│   ├── phase_5b_dashboard/
│   │   └── dashboard_events_633.csv   # Source dataset (copied or symlinked to public/data/)
│   └── phase_6/
│       ├── PHASE_6_STEP_1_FRONTEND_AUDIT.md
│       └── PHASE_6_STEP_2_FRONTEND_ARCHITECTURE.md
├── src/                               # Python backend and pipelines
└── frontend/                          # [NEW in Step 3] Complete Web Application
    ├── index.html                     # Web entry point (Inter font, Leaflet CSS, viewport)
    ├── package.json                   # Dependencies and npm scripts (dev, build, preview)
    ├── tsconfig.json                  # TypeScript compiler settings
    ├── tsconfig.node.json             # TypeScript settings for Vite config
    ├── vite.config.ts                 # Vite config with dev proxy (/api -> http://127.0.0.1:8000)
    ├── .env.example                   # Client environment template (VITE_API_BASE_URL, VITE_API_KEY)
    ├── public/
    │   ├── data/
    │   │   └── dashboard_events_633.csv # Static asset served directly to browser
    │   └── favicon.svg
    └── src/
        ├── main.tsx                   # React root mount
        ├── App.tsx                    # Primary layout orchestrator
        ├── index.css                  # Design tokens, dark theme, resets, animations
        ├── types/
        │   ├── dashboard.ts           # Interfaces for all 61 dashboard dataset fields
        │   ├── api.ts                 # Interfaces for /health and /predict contracts
        │   └── filters.ts             # Filter state criteria interfaces
        ├── services/
        │   ├── dataLoader.ts          # PapaParse loader with null sanitation & type guards
        │   └── apiService.ts          # Fetch client for GET /health and POST /predict
        ├── hooks/
        │   ├── useDashboardData.ts    # Custom hook: loads CSV, manages loading/error states
        │   ├── useFilters.ts          # Custom hook: multi-facet filtering memoization
        │   └── useBackendHealth.ts    # Custom hook: polls /health and stores connection state
        ├── utils/
        │   ├── formatters.ts          # Coordinate, date, FRP, distance, percentage formatters
        │   ├── colorMap.ts            # Official class colors, confidence badges, landcover tags
        │   └── exportUtils.ts         # Filtered events GeoJSON / CSV exporter
        └── components/
            ├── common/
            │   ├── Badge.tsx          # Reusable status/tier pill badge
            │   ├── StatCard.tsx       # KPI counter tile
            │   ├── Modal.tsx          # Accessible dialog modal
            │   └── Spinner.tsx        # Loading indicator
            ├── layout/
            │   ├── Header.tsx         # Navbar with title, SIH badge, and health pill
            │   ├── SummaryBar.tsx     # KPI summary metrics strip
            │   └── DisclaimerBar.tsx  # Mandatory ML algorithmic estimate disclaimer
            ├── map/
            │   ├── FireMap.tsx        # Main Leaflet map canvas with Tamil Nadu center
            │   ├── EventMarker.tsx    # SVG circle markers color-coded by 3 ML classes
            │   ├── MapLegend.tsx      # Floating legend explaining classes and marker sizing
            │   └── MapControls.tsx    # Basemap toggle (Dark / Satellite / Positron)
            ├── filters/
            │   ├── FilterPanel.tsx    # Collapsible sidebar with multi-facet controls
            │   ├── FilterSection.tsx  # Accordion group for filter categories
            │   ├── RangeSlider.tsx    # Continuous FRP range slider
            │   └── FilterPills.tsx    # Active filter chips with individual & clear-all remove
            ├── inspector/
            │   ├── EventDrawer.tsx    # Slide-over inspector panel (61 fields across 9 groups)
            │   ├── TabNavigation.tsx  # Drawer tabs: Overview, Thermal, Context, Sentinel-2, Audit
            │   ├── PredictionCard.tsx # 3-class probability bars, winning prob, ML confidence
            │   ├── ThermalCard.tsx    # VIIRS sensor metrics, FRP, persistence, brightness
            │   ├── OsmCard.tsx        # Industrial proximity, facility category, relevance tier
            │   ├── LandcoverCard.tsx  # ESA WorldCover class and code
            │   ├── SentinelCard.tsx   # Optical change, NDVI pre/post, dNBR, cloud notice
            │   └── GroundTruthCard.tsx# Expert human validation review card (if validated)
            └── live/
                └── LivePredictModal.tsx # On-demand ML inference modal with 36-feature schema
```

---

## 3. Component Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                       App.tsx                                          │
│  State: events[], selectedEventId, filters, backendHealth, isLiveModalOpen, isLoading  │
└────────────────────────────────────────────────────────────────────────────────────────┘
  │
  ├─── <Header />
  │      ├── Branding & SIH Title
  │      ├── <BackendHealthIndicator />  (Polls GET /api/v1/health -> Status Pill)
  │      └── Live Inference Trigger Button (Opens <LivePredictModal />)
  │
  ├─── <SummaryBar />
  │      └── KPI Counters (Total 633, Industrial Active, Agricultural, Natural, Validated, S2)
  │
  ├─── <main className="dashboard-body">
  │      │
  │      ├─── <FilterPanel />  (Left Sidebar - Collapsible)
  │      │      ├── Class Multi-select (3 ML Classes)
  │      │      ├── ML Confidence Tier (HIGH / MEDIUM / LOW)
  │      │      ├── FIRMS Sensor Confidence (h / n / l)
  │      │      ├── Landcover Class Multi-select
  │      │      ├── Facility Relevance Tier
  │      │      ├── Persistence Hotspot Toggle (grid_active_days >= 3)
  │      │      ├── Human Validation Filter (has_human_validation == true)
  │      │      ├── Sentinel-2 Data Available (s2_change_status == SUCCESS)
  │      │      ├── FRP Range Slider (min_frp - max_frp)
  │      │      └── <FilterPills /> (Active tag chips + Reset button)
  │      │
  │      ├─── <FireMap />  (Center Map View - Leaflet)
  │      │      ├── TileLayer (CartoDB Dark Matter / Satellite)
  │      │      ├── EventMarkers[] (Filtered events rendered with 3-class color coding)
  │      │      ├── Selection Halo (Animated ring on selectedEvent)
  │      │      └── <MapLegend /> (Floating class color key & size explanation)
  │      │
  │      └─── <EventDrawer />  (Right Slide-over Inspector - 61 Fields)
  │             ├── Drawer Header (event_id, date/time, close button)
  │             ├── <PredictionCard /> (3-Class Probabilities, Winning %, ML Confidence)
  │             ├── <ThermalCard /> (FIRMS VIIRS, FRP, Brightness, Persistence Flag)
  │             ├── <OsmCard /> (Nearest Facility Name, Category, Tier, Distance)
  │             ├── <LandcoverCard /> (ESA WorldCover Name & Code)
  │             ├── <SentinelCard /> (Optical change, NDVI pre/post, dNBR, Cloud status)
  │             ├── <GroundTruthCard /> (Human review class, validation status)
  │             └── <ProvenanceCard /> (Inference timestamp, model SHA-256)
  │
  ├─── <LivePredictModal />  (Dialog for live POST /api/v1/predict testing)
  │      ├── 36-Feature Form (Pre-fillable from selectedEvent)
  │      ├── Payload Validator (Ensures no target leakage fields)
  │      └── Result Viewer (Real-time probability breakdown & confidence)
  │
  └─── <DisclaimerBar />
         └── "Prediction is an algorithmic ML estimate. It is not ground truth."
```

---

## 4. Dual-Track Data Flow Specification

The architecture strictly decouples the static historical dashboard dataset from live API inference:

```
TRACK 1: STATIC HISTORICAL DASHBOARD PIPELINE (Instant, Offline-Capable)
──────────────────────────────────────────────────────────────────────────
  outputs/phase_5b_dashboard/dashboard_events_633.csv (633 rows × 61 cols)
                           │
                           ▼ [public/data/dashboard_events_633.csv]
                      dataLoader.ts (PapaParse with Web Worker)
                           │
                           ▼
                    DashboardEvent[] (Raw Array in React State)
                           │
                           ▼
           useFilters() [Memoized Multi-Facet Filtering]
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
      FireMap.tsx                    SummaryBar.tsx
   (Plots 633 Markers)            (Calculates Active KPIs)
           │
           ▼ [User clicks marker]
     selectedEvent (DashboardEvent)
           │
           ▼
     EventDrawer.tsx (Displays 61 fields in 9 groups)


TRACK 2: LIVE ON-DEMAND ML INFERENCE PIPELINE (Network-Driven)
──────────────────────────────────────────────────────────────────────────
     User opens LivePredictModal.tsx (or selects an event to re-evaluate)
                           │
                           ▼
         Construct 36 Baseline Features JSON Payload
       (Explicitly omit leakage fields: human_*, ml_target_*)
                           │
                           ▼
        apiService.predictEvent(payload, apiKey)
                           │
                           ▼ [HTTP POST /api/v1/predict with X-API-Key]
                 FastAPI Backend (`src/api/main.py`)
                           │
                           ▼ [Calls predict_event()]
                  src/models/predict.py
                           │
                           ▼ [Evaluates Pipeline]
             final_model.joblib (SHA-256: 5909bb546f...)
                           │
                           ▼ [HTTP 200 OK Response]
                  PredictResponse Interface
                           │
                           ▼
     Display live predicted class, 3 probabilities, and ML confidence
```

---

## 5. TypeScript Data Models

The following TypeScript interfaces must be created in `frontend/src/types/`:

### 5.1 Authoritative 61-Column Dashboard Event Interface (`types/dashboard.ts`)

```typescript
export interface DashboardEvent {
  // GROUP A — EVENT IDENTITY (6 fields)
  event_id: string;                         // e.g. "FIRMS_TN_0000"
  row_id: number;                           // Sequential 0-632
  acq_date: string;                         // "YYYY-MM-DD"
  acq_time: number;                         // UTC HHMM e.g. 745
  acq_datetime: string;                     // ISO datetime
  daynight: "D" | "N";                      // Daytime / Nighttime

  // GROUP B — LOCATION (2 fields)
  latitude: number;                         // WGS84 Latitude (8°N - 14°N)
  longitude: number;                        // WGS84 Longitude (76°E - 81°E)

  // GROUP C — FIRMS THERMAL EVIDENCE (15 fields)
  satellite: string;                        // "N20", "NOAA-21", "SNPP"
  instrument: string;                       // "VIIRS"
  firms_confidence: "h" | "n" | "l";        // Satellite sensor confidence
  frp: number;                              // Fire Radiative Power (MW)
  brightness: number;                       // I4 channel temperature (K)
  bright_t31: number;                       // I5 channel temperature (K)
  brightness_difference: number;            // I4 - I5 (K)
  is_day: 0 | 1;                            // 1 = day, 0 = night
  is_stubble_burning_season: 0 | 1;         // Seasonal agricultural indicator
  grid_detection_count: number;             // Historical detection count in grid
  grid_active_days: number;                 // Distinct active days in grid
  persistent_location_flag: 0 | 1;          // 1 = active days >= 3
  grid_total_frp: number;                   // Cumulative FRP in grid
  high_frp_flag_local: 0 | 1;               // Local anomaly spike flag
  brightness_zscore_local: number;          // Standardized brightness score

  // GROUP D — ML PREDICTION (6 fields)
  predicted_class: ProductionClass;         // Official 3-class prediction
  probability_agricultural_burning: number; // Probability [0, 1]
  probability_industrial_thermal_activity: number; // Probability [0, 1]
  probability_natural_wildfire_other: number;      // Probability [0, 1]
  max_probability: number;                  // Winning class probability [0, 1]
  ml_confidence: ConfidenceTier;            // "HIGH" | "MEDIUM" | "LOW"

  // GROUP E — OSM INDUSTRIAL CONTEXT (12 fields)
  osm_coverage_status: "COVERED" | "FAILED_TILE";
  nearest_facility_name: string | null;     // null -> display "Unknown"
  nearest_facility_type: string;            // OSM tag e.g. "industrial"
  nearest_facility_category: string;        // e.g. "Steel / Metallurgy"
  nearest_facility_tier: FacilityTier;      // "HIGHER_RELEVANCE" | "CAUTION_LOWER_RELEVANCE" | "GENERAL_CONTEXT"
  distance_to_facility_m: number;           // Distance in meters
  near_industrial_500m: 0 | 1;              // Proximity flags
  near_industrial_1000m: 0 | 1;
  near_industrial_2000m: 0 | 1;
  nearest_hr_category: string;              // Category of nearest high-relevance facility
  nearest_hr_name: string | null;           // null -> display "Unknown"
  distance_to_higher_relevance_m: number;   // Meters to high-relevance facility

  // GROUP F — WORLDCOVER (2 fields)
  landcover_code: number;                   // ESA WorldCover code (10, 20, 30, 40, 50, 60)
  landcover_class: string;                  // "Built-up", "Cropland", "Tree cover", etc.

  // GROUP G — SENTINEL-2 (10 fields)
  pre_observation_status: ObservationStatus;  // "REAL_CDSE_SUCCESS" | "CLOUD_REJECTED" | "MISSING_PRODUCT"
  post_observation_status: ObservationStatus; // "REAL_CDSE_SUCCESS" | "CLOUD_REJECTED" | "MISSING_PRODUCT"
  s2_change_status: S2ChangeStatus;           // "SUCCESS" | "MISSING_POST" | "CLOUD_REJECTED", etc.
  selected_pre_image_date: string | null;     // ISO date or null
  selected_post_image_date: string | null;    // ISO date or null
  s2_pre_feature_status: string | null;       // Extraction status or null
  s2_post_feature_status: string | null;      // Extraction status or null
  s2_pre_ndvi_mean: number | null;            // Mean NDVI or null
  s2_post_ndvi_mean: number | null;           // Mean NDVI or null
  s2_dnbr_mean: number | null;                // Burn severity dNBR or null

  // GROUP H — HUMAN VALIDATION (4 fields)
  has_human_validation: boolean;            // true for 100/633 events
  human_validation_status: "VERIFIED" | "UNREVIEWED";
  human_ground_truth_class: string | null;  // 6-class raw human review label or null
  is_unambiguous_ground_truth: boolean;     // true for 76 clean training samples

  // GROUP I — PROVENANCE (4 fields)
  inference_timestamp: string;              // ISO UTC
  model_version: string;                    // "phase_5_ml_handoff/final_model.joblib"
  model_sha256: string;                     // "5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798"
  data_source_version: string;              // "phase_4b_ground_truth_v1"
}

export type ProductionClass =
  | "Industrial Thermal Activity"
  | "Agricultural Burning"
  | "Natural / Wildfire / Other";

export type ConfidenceTier = "HIGH" | "MEDIUM" | "LOW";

export type FacilityTier =
  | "HIGHER_RELEVANCE"
  | "CAUTION_LOWER_RELEVANCE"
  | "GENERAL_CONTEXT"
  | "NO_FACILITY_FOUND";

export type ObservationStatus =
  | "REAL_CDSE_SUCCESS"
  | "CLOUD_REJECTED"
  | "MISSING_PRODUCT";

export type S2ChangeStatus =
  | "SUCCESS"
  | "MISSING_PRE"
  | "MISSING_POST"
  | "CLOUD_REJECTED"
  | "INSUFFICIENT_VALID_DATA";
```

### 5.2 API Contracts & Types (`types/api.ts`)

```typescript
export interface HealthResponse {
  status: "ok" | "unavailable";
  model_loaded: boolean;
  model_version: string;
  model_sha256: string;
  required_features_count: number;
  production_classes: ProductionClass[];
  api_version: string;
  timestamp: string;
}

export interface PredictRequest {
  event_id?: string;
  features: Record<string, number | string>; // Exactly the 36 baseline features
}

export interface PredictResponse {
  event_id?: string;
  predicted_class: ProductionClass;
  probabilities: {
    "Agricultural Burning": number;
    "Industrial Thermal Activity": number;
    "Natural / Wildfire / Other": number;
  };
  max_probability: number;
  ml_confidence: ConfidenceTier;
  confidence_scale: {
    HIGH: string;
    MEDIUM: string;
    LOW: string;
  };
  model: {
    version: string;
    sha256: string;
    architecture: string;
    training_samples: number;
    macro_f1_oof: number;
  };
  inference_timestamp: string;
  disclaimer: string;
}

export interface APIErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
```

---

## 6. Interactive GIS Map Design

### 6.1 Geographic Extent & Viewport:
- **Map Library:** Leaflet 1.9.4 bound via React-Leaflet 4.2.1.
- **Center Coordinate:** `[11.1271, 78.6569]` (Geographic centroid of Tamil Nadu, India).
- **Initial Zoom Level:** `7` (Full-state boundary overview from Chennai to Kanyakumari).
- **Max Bounds:** `[[7.5, 75.5], [14.0, 81.5]]` (Prevents excessive panning beyond southern India).
- **Tile Providers:**
  - *Primary (Default):* CartoDB Dark Matter (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`) — High contrast for glowing thermal hotspots.
  - *Secondary:* ESRI World Imagery (Satellite tiles for inspecting physical factory/agricultural landscape).

### 6.2 Marker Styling by Official ML Class:
The map renders strictly the **3 official ML production classes**. Sub-classes or 6-class heuristics must **never** be rendered as ML predictions:

| Production Class | Marker Fill Color | Glow / Halo Color | Visual Theme |
|---|---|---|---|
| **Industrial Thermal Activity** | `#EF4444` (Crimson-Red) | `rgba(239, 68, 68, 0.4)` | Factory / Heavy Heat |
| **Agricultural Burning** | `#F59E0B` (Harvest-Amber) | `rgba(245, 158, 11, 0.4)` | Stubble / Field Smoke |
| **Natural / Wildfire / Other** | `#10B981` (Emerald-Green) | `rgba(16, 185, 129, 0.4)` | Forest / Vegetation |

### 6.3 Marker Scaling & Interactivity:
- **Marker Radius:** Base radius = 5px, dynamically scaled:
  $$\text{Radius} = 4 + \min(6, \sqrt{\text{FRP}} \times 1.2)$$
- **Marker Stroke Opacity:** Driven by `ml_confidence`:
  - `HIGH`: Stroke weight 2.5px, opacity 1.0 (crisp outline).
  - `MEDIUM`: Stroke weight 1.5px, opacity 0.8.
  - `LOW`: Stroke weight 1.0px, opacity 0.5.
- **Persistent Location Indicator:** If `persistent_location_flag == 1`, render an animated concentric pulse ring around the marker.
- **Selection State:** Clicking an event marker sets `selectedEventId` in React state, smoothly centers the map on the coordinate, applies an active highlight ring, and slides open the `<EventDrawer />`.

---

## 7. Multi-Facet Filter Architecture

All filters operate purely against verified fields in `dashboard_events_633.csv`. No unverified fields are permitted:

```typescript
export interface FilterCriteria {
  searchQuery: string;                      // Matches event_id, nearest_facility_name, or nearest_facility_category
  classes: ProductionClass[];               // Empty array = all classes
  confidenceTiers: ConfidenceTier[];        // ["HIGH", "MEDIUM", "LOW"]
  firmsConfidences: ("h" | "n" | "l")[];    // Satellite sensor certainty
  dayNight: ("D" | "N")[];                  // Daytime vs Nighttime
  landcoverClasses: string[];               // "Built-up", "Cropland", "Tree cover", etc.
  facilityTiers: FacilityTier[];            // "HIGHER_RELEVANCE", "CAUTION_LOWER_RELEVANCE", etc.
  onlyPersistentHotspots: boolean;          // persistent_location_flag == 1
  onlyHumanValidated: boolean;              // has_human_validation == true
  onlyS2Available: boolean;                 // s2_change_status == "SUCCESS"
  frpRange: [number, number];               // [min_frp, max_frp] (~0.3 to 45.0 MW)
}
```

### Filter Execution Pipeline:
- Implemented inside `useFilters()` hook with `useMemo()`.
- Evaluates 633 records in < 2 milliseconds.
- Provides an **Active Filter Pills Bar** enabling users to dismiss individual filters or click "Reset All Filters".

---

## 8. Event Detail Drawer Architecture (61 Fields in 9 Groups)

When an operator clicks an event marker, `<EventDrawer />` slides in from the right edge, presenting all 61 fields in 9 structured sections:

```
┌────────────────────────────────────────────────────────────────────────┐
│ EVENT INSPECTOR: FIRMS_TN_0000                        [✕ Close]        │
│ 2024-11-01 19:40 UTC | Nighttime Overpass | Lat: 11.664° Lon: 78.071°   │
├────────────────────────────────────────────────────────────────────────┤
│ [CARD 1: ML PREDICTION (Group D)]                                      │
│ ML Prediction: INDUSTRIAL THERMAL ACTIVITY                             │
│ Winning Probability: 50.3% | ML Confidence: MEDIUM                    │
│                                                                        │
│ Industrial Thermal: ████████████░░░░░░░░░░░░ 50.3%                     │
│ Agricultural Burn:  ██████████░░░░░░░░░░░░░░ 43.3%                     │
│ Natural / Wildfire: █░░░░░░░░░░░░░░░░░░░░░░░  6.4%                     │
│                                                                        │
│ ⚠️ Disclaimer: Prediction is an algorithmic ML estimate. Not ground truth│
├────────────────────────────────────────────────────────────────────────┤
│ [CARD 2: THERMAL SIGNAL EVIDENCE (Group C)]                            │
│ • Fire Radiative Power (FRP): 1.16 MW      • Sensor Confidence: h (High)│
│ • I4 Brightness: 312.4 K                   • Background (I5): 294.2 K  │
│ • Temperature Anomaly: +18.2 K             • Historical Days: 14 days  │
│ • Persistence: MULTI-DAY HOTSPOT (Active)  • Cell FRP: 28.4 MW         │
├────────────────────────────────────────────────────────────────────────┤
│ [CARD 3: OSM INDUSTRIAL CONTEXT (Group E)]                             │
│ • Nearest Facility: Steel Authority of India Ltd (SAIL)                │
│ • Facility Category: Steel / Metallurgy    • Type: industrial          │
│ • Proximity Tier: HIGHER_RELEVANCE         • Distance: 328 meters      │
│ • Proximity Flags: <500m [YES]  <1000m [YES]  <2000m [YES]             │
├────────────────────────────────────────────────────────────────────────┤
│ [CARD 4: LAND SURFACE CONTEXT (Group F)]                               │
│ • Landcover Class: Built-up (ESA WorldCover Code: 50)                  │
├────────────────────────────────────────────────────────────────────────┤
│ [CARD 5: SENTINEL-2 OPTICAL EVIDENCE (Group G)]                        │
│ • Optical Change Status: SUCCESS           • Pre-Image: 2024-10-28     │
│ • Pre-NDVI: 0.18 | Post-NDVI: 0.17         • Post-Image: 2024-11-02    │
│ • Burn Severity (dNBR): +0.008 (Near-zero / Fixed industrial structure)│
│ ℹ️ Context: Sentinel-2 provides optical surface context, not thermal IR│
├────────────────────────────────────────────────────────────────────────┤
│ [CARD 6: HUMAN EXPERT VALIDATION (Group H)]                            │
│ • Review Status: VERIFIED                                              │
│ • Expert Ground Truth Label: Persistent Industrial Thermal Source      │
│ • Review Certainty: Unambiguous Ground Truth                           │
├────────────────────────────────────────────────────────────────────────┤
│ [CARD 7: PROVENANCE & AUDIT TRAIL (Groups A & I)]                      │
│ • Event ID: FIRMS_TN_0000                  • Pipeline: Phase 5B v1     │
│ • Model SHA-256: 5909bb546fc55aeffd37b7bb601e96718709fe685e9877...     │
│ • Inference Time: 2026-09-06T18:18:49Z                                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. FastAPI Backend Integration Architecture

### 9.1 Base Configuration:
- **Base URL:** Defined via `VITE_API_BASE_URL` in `.env` (defaults to `/api` in development, proxied by Vite to `http://127.0.0.1:8000`).
- **API Key:** Defined via `VITE_API_KEY` in `.env` (defaults to `test-api-key-phase5c`). Never hard-coded into public Git files.

### 9.2 Endpoint 1: `GET /api/v1/health`
- **Polling Strategy:** Polled once on application mount and every 30 seconds thereafter.
- **UI Element:** `<BackendHealthIndicator />` in the top navbar:
  - `status == "ok"` and `model_loaded == true`: Green pulsing pill (`● Backend Ready | Model Verified`).
  - Tooltip: Displays model architecture (`Random Forest`), required features count (`36`), and SHA-256 digest (`5909bb54...`).
  - Network failure or HTTP 503: Amber/Red pill (`Backend Offline`).

### 9.3 Endpoint 2: `POST /api/v1/predict`
- **Component:** `<LivePredictModal />`.
- **Payload Sanitization:** Form strictly constructs the 36 baseline features. It strips all human validation fields (`human_*`) and target leakage fields (`ml_target_3class`) before dispatching the request.
- **Request Headers:**
  - `Content-Type: application/json`
  - `X-API-Key: <VITE_API_KEY>`
- **Response Handling:** Renders probability breakdown bar, winning probability, confidence tier, and inference latency in milliseconds.

---

## 10. Scientific Display Rules & Presentation Guardrails

The frontend must strictly enforce the following scientific guidelines:

1. **Disambiguate the 3 Confidence Metrics:**
   - **`firms_confidence`** = Label as **"Satellite Sensor Confidence"** (NASA VIIRS detection certainty: High, Nominal, Low).
   - **`max_probability`** = Label as **"Winning ML Probability"** (Direct mathematical probability: `0.0%` – `100.0%`).
   - **`ml_confidence`** = Label as **"ML Confidence Tier"** (Operational category: `HIGH`, `MEDIUM`, `LOW`).
   - **Never collapse or combine these three metrics.**
2. **Strictly 3 Production ML Classes:**
   - Always display `Industrial Thermal Activity`, `Agricultural Burning`, and `Natural / Wildfire / Other`.
   - Never fabricate sub-classes for ML output.
3. **Accurate Sentinel-2 Representation:**
   - Sentinel-2 MSI provides optical and near-infrared surface context.
   - **Never describe Sentinel-2 as a thermal detector.** Thermal fire detection is performed exclusively by the 375m VIIRS sensor.
   - When optical data was rejected due to clouds (`pre_observation_status == "CLOUD_REJECTED"`), display: *"Optical imagery obstructed by cloud cover during satellite overpass."*
4. **Mandatory Algorithmic Disclaimer:**
   - Render in the footer and inside every prediction card:  
     > *"Prediction is an algorithmic ML estimate. It is not ground truth."*

---

## 11. Responsive Layout Specifications

| Device / Viewport | Layout Mode | Component Layout Behavior |
|---|---|---|
| **Desktop Ultra-wide (≥1440px)** | Full 3-Pane View | Filter sidebar fixed on left (280px), interactive map expands to fill center, event drawer docks permanently on right (460px) upon event selection. |
| **Standard Laptop (1024px – 1439px)** | 2-Pane + Slide-over | Filter panel collapsible via toggle button, map fills 100% width, event drawer slides over map from right (420px) with backdrop blur. |
| **Tablet / Small Laptop (768px – 1023px)** | Stacked / Floating | Map occupies upper 60% of viewport; drawer opens as bottom sheet / modal with swipe-down dismissal. |

---

## 12. Performance Considerations for 633 Records

1. **CSV Ingestion:** PapaParse parses the 420 KB CSV file in ~18 milliseconds. Data is loaded once on app boot and held in React memory.
2. **Marker Rendering:** Leaflet handles 633 `CircleMarker` instances effortlessly (< 5% CPU utilization). Canvas rendering mode (`L.canvas()`) will be enabled on the `MapContainer` to ensure 60 FPS smooth zooming and panning.
3. **Filter Reactivity:** `useMemo` computes the filtered subset of 633 events in < 2ms, providing instant zero-lag response as the user drags the FRP slider or toggles checkboxes.
4. **Bundle Footprint:** Without heavy dependencies, the production Vite bundle will be under 220 KB gzipped, loading in under 400 ms.

---

## 13. Smart India Hackathon (SIH) Jury Presentation Flow

The dashboard is structured to support a compelling 2-minute live jury demonstration:

1. **Initial Overview (State-Level View):**
   - Open dashboard. 633 thermal anomaly hotspots populate across Tamil Nadu over CartoDB dark basemap.
   - Point to the navbar: green health indicator confirms FastAPI backend is online and model SHA-256 is verified.
2. **Filter to Industrial Candidates:**
   - Click filter: Landcover = `Built-up`, Facility Tier = `HIGHER_RELEVANCE`, Persistence = `Active (>=3 days)`.
   - The map instantaneously filters down from 633 to the core industrial clusters in Tamil Nadu (Salem, Mettur, Ennore, Tuticorin).
3. **Select Salem Steel Plant Anomaly (`FIRMS_TN_0000`):**
   - Click the prominent red marker at `[11.664, 78.071]`.
   - Map zooms and centers smoothly; `<EventDrawer />` slides in.
4. **Walkthrough Multi-Modal Evidence:**
   - *Thermal:* VIIRS 375m detection, FRP = 1.16 MW, persistent active hotspot across 14 days.
   - *OSM Context:* Facility = SAIL / Salem Steel Plant (328m away, `HIGHER_RELEVANCE`).
   - *WorldCover:* Built-up surface (Class 50).
   - *Sentinel-2 Context:* Optical change status verified (`s2_dnbr_mean` = +0.008, indicating fixed operational structure rather than vegetative burn).
5. **Demonstrate 3-Class ML Prediction:**
   - ML Prediction: **Industrial Thermal Activity** (50.3% winning probability, Medium confidence).
   - Show how the model fused spatial persistence, facility proximity, and landcover to correctly classify the industrial event.
6. **Showcase Independent Human Validation:**
   - Highlight the human validation card: expert review confirmed label as *"Persistent Industrial Thermal Source"*.
   - Point out that ML prediction and human ground truth are kept distinct and verifiable.
7. **Live Inference Demonstration:**
   - Click "Live Inference Test" in navbar.
   - Click "Populate with Salem Steel Event".
   - Modify FRP or proximity slightly and hit "Run Live Inference".
   - Live HTTP POST request to FastAPI returns sub-25ms inference result directly from `final_model.joblib`.

---

## 14. Phase 6 Step 3 Implementation Plan

With the architecture specification complete, the next step (Step 3) will execute the baseline scaffolding:

1. **Initialize Project:** Run Vite initialization in `frontend/` using `npm create vite@latest frontend -- --template react-ts`.
2. **Install Production Dependencies:**
   - `leaflet`, `react-leaflet`, `@types/leaflet`
   - `papaparse`, `@types/papaparse`
   - `lucide-react`
3. **Configure Build & Dev Tooling:**
   - Set up `vite.config.ts` with API reverse proxy `/api` targeting `http://127.0.0.1:8000`.
   - Create `frontend/.env.example` with `VITE_API_KEY` and `VITE_API_BASE_URL`.
4. **Copy Authoritative Data Asset:**
   - Place `outputs/phase_5b_dashboard/dashboard_events_633.csv` into `frontend/public/data/`.
5. **Implement Core Design System & Tokens:**
   - Write `frontend/src/index.css` with dark theme variables, typography (Inter), glassmorphic panels, and animations.
6. **Implement TypeScript Interfaces:**
   - Create `frontend/src/types/dashboard.ts`, `api.ts`, and `filters.ts` strictly matching this specification.
7. **Verify Local Build:**
   - Run `npm run build` to confirm zero compilation or type errors.

---
*End of Phase 6 Step 2 Frontend Architecture Document.*
