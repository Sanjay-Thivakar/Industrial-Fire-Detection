# Industrial Fire Detection & Classification System
## Comprehensive Dashboard UI Feature Explanation & Judge's Guide

**Project:** Industrial Fire Detection & Classification System  
**Competition / Context:** Smart India Hackathon (SIH) — Tamil Nadu Region Deployment  
**Authoritative Reference:** Phase 5B Production Baseline & Phase 5C Live Inference Microservice  
**Document Purpose:** Complete, judge-friendly explanation of all user-facing interface elements, scientific guardrails, data lineages, and operational workflows.

---

## Executive Summary & Design Philosophy

The **Industrial Fire Detection & Classification System** dashboard provides environmental officers, disaster management authorities, and hackathon evaluation judges with a multi-modal Geographic Information System (GIS) command interface. 

Rather than treating Machine Learning (ML) as an infallible "black box," the dashboard implements an **evidence-based decision support framework**. It fuses thermal satellite radiometry, optical surface change verification, crowdsourced infrastructure GIS, and high-resolution land-cover maps into a transparent, audit-ready operational workspace.

---

## 1. Header & Top Navigation

The global header anchors the interface across all display resolutions, providing immediate situational awareness and live service telemetry.

| Element | Current UI Display | Data Source / Mechanism | Scientific & Operational Purpose |
| :--- | :--- | :--- | :--- |
| **System Branding** | `Industrial Fire Detection & Classification System` | Static Application Metadata | Establishes the authoritative title of the decision-support platform. |
| **Subtitle** | `Interactive Multi-Modal GIS Dashboard • Smart India Hackathon` | Static Application Metadata | Clarifies the target operational domain and engineering competition scope. |
| **Demo Quick Picks** | Quick preset buttons (`⚡ Demo Quick Picks:`) | Curated benchmark events from authoritative dataset | Enables presenters and judges to jump directly to representative industrial and agricultural test cases in one click. |
| **Notice Banner** | Dismissible yellow alert bar | UI State Controller (`quickPickNotice`) | Alerts the user if active sidebar filters had to be automatically reset to reveal a requested demo event on the map. |
| **Backend Health Badge** | `🟢 ML Backend: Online (v1.0.0)` or `🔴 ML Backend: Offline` | Periodic polling (`GET /api/v1/health` every 10s) | Live connection status to the Python FastAPI microservice; verifies that the scikit-learn model artifact is loaded in backend memory. |
| **Dataset Counter Badge** | `Dataset Active: 633 Events` (Green) or `Showing: X of 633` (Amber) | Dynamic count of events surviving active filters | Informs the user whether they are inspecting the complete regional baseline or a filtered operational subset. |
| **Model Badge** | `Random Forest (3 ML Classes)` | Backend Model Architecture Metadata | Communicates the machine learning classification model tier without technical jargon. |

---

## 2. Summary & Key Performance Indicator (KPI) Bar

Positioned directly beneath the header, the KPI Bar delivers instant statistical aggregation across the filtered cohort of thermal events.

```
[ Events: 633 ]  |  [ ● Industrial: 36 ]  |  [ ● Agricultural: 585 ]  |  [ ● Natural: 12 ]  |  [ High Conf: 618 ]  |  [ Avg FRP: 6.84 MW ]
```

### KPI Metric Breakdown:

1. **Total Events (`Events:`)**
   - **What it represents:** The total count of thermal detections currently matching all active sidebar filters and rendered on the map.
   - **Data Source:** `filteredEvents.length` out of the 633 authoritative Tamil Nadu baseline events.
   - **Judge Value:** Proves that the dashboard is reactive and dynamic; adjusting any filter instantly recalculates this metric.

2. **Industrial Thermal Activity (`Industrial:`)**
   - **What it represents:** Count of active events classified as industrial combustion, furnace emissions, flaring, or metallurgical activity.
   - **Data Source:** Evaluated where `predicted_class === 'Industrial Thermal Activity'`.
   - **Judge Value:** Rapidly isolates potential compliance violations or industrial emissions from ubiquitous rural biomass burning.

3. **Agricultural Burning (`Agricultural:`)**
   - **What it represents:** Count of active events classified as seasonal open-field crop residue or stubble burning.
   - **Data Source:** Evaluated where `predicted_class === 'Agricultural Burning'`.
   - **Judge Value:** Highlights seasonal rural burning patterns (e.g., paddy residue management), which constitute the vast majority of regional thermal anomalies.

4. **Natural / Wildfire / Other (`Natural:`)**
   - **What it represents:** Count of active events classified as forest fires, scrubland blazes, or unclassified rural burns.
   - **Data Source:** Evaluated where `predicted_class === 'Natural / Wildfire / Other'`.
   - **Judge Value:** Separates open forest fires (which require forest department firefighting) from industrial facility monitoring.

5. **High Confidence (`High Conf:`)**
   - **What it represents:** Number of detections where the winning ML class probability meets or exceeds the strict production threshold of **75.0%** ($P \ge 0.75$).
   - **Data Source:** Evaluated where `ml_confidence === 'HIGH'`.
   - **Judge Value:** Informs emergency response teams which events have strong statistical agreement across multiple feature modalities.

6. **Average Fire Radiative Power (`Avg FRP:`)**
   - **What it represents:** The arithmetic mean of radiant heat energy output across all currently visible thermal events, expressed in Megawatts (MW).
   - **Data Source:** $\frac{1}{N}\sum \text{FRP}_i$ computed across `filteredEvents`.
   - **Judge Value:** Quantifies aggregate thermal intensity across the state or a specific district.

---

## 3. Interactive GIS Map Viewport

The primary workspace is an interactive map rendered via **Leaflet** with high-performance HTML5 Canvas marker rendering (`preferCanvas={true}`), ensuring smooth 60 FPS panning and zooming even with hundreds of active hotspots.

### Key Map Capabilities:

- **Geographic Center & Bounds:** Tamil Nadu, Southern India (initial centroid calculated dynamically from dataset at $\approx 11.13^\circ\text{N}, 78.66^\circ\text{E}$; min zoom 6, max zoom 15).
- **Basemap:** OpenStreetMap (OSM) standard cartographic tile layer providing road networks, administrative boundaries, water bodies, and settlement footprints.
- **Marker Symbolization:**
  - **Color:** Strict visual tri-color coding matching the 3 production classes:
    - 🔴 **Crimson Red (`#ef4444`):** Industrial Thermal Activity
    - 🟠 **Harvest Amber (`#f59e0b`):** Agricultural Burning
    - 🟢 **Forest Emerald (`#10b981`):** Natural / Wildfire / Other
  - **Dynamic Radius:** Proportional to Fire Radiative Power (FRP):
    $$\text{Radius (pixels)} = \min\left(10, \max\left(4, 3 + 1.2 \times \sqrt{\text{FRP}}\right)\right)$$
    *Intuition:* A low-intensity 1.5 MW field burn displays as a compact 4.5px circle, whereas a fierce 40 MW furnace or refinery flare scales to a bold 10px circular marker.
  - **Selection State:** Clicking any marker highlights it with a brilliant white stroke border (`#ffffff`, 3px weight), boosts fill opacity to 0.95, smoothly centers the map view (`panTo` with 0.4s ease), and opens the Event Detail Drawer.
  - **Popup Management:** When clicking markers to inspect details, map popups are automatically suppressed to avoid visual clutter and double-popup obstruction over the drawer.

---

## 4. Multi-Facet Filtering Sidebar

The collapsible filter sidebar on the left gives users multi-dimensional control to test hypotheses, audit edge cases, and isolate specific operational scenarios.

### Filter Dimensions:

| Filter Section | Available Options | Scientific Rationale | Demo Use Case |
| :--- | :--- | :--- | :--- |
| **ML Prediction Class** | • Industrial Thermal Activity<br>• Agricultural Burning<br>• Natural / Wildfire / Other | Isolates specific threat categories or operational domains. | Uncheck "Agricultural" and "Natural" to show ONLY industrial hotspots in Tamil Nadu. |
| **ML Confidence Tier** | • HIGH ($\ge 75\%$) <br>• MEDIUM ($50\% - 74\%$) <br>• LOW ($< 50\%$) | Assesses model certainty and filters out borderline classifications. | Select "LOW" to inspect difficult edge cases where features disagree. |
| **Satellite Sensor Certainty** | • High (`h`)<br>• Nominal (`n`)<br>• Low (`l`) | FIRMS detection algorithm certainty based on radiometric scan geometry and background contrast. | Filter for `h` only to ensure zero false radiometric detections from sensor noise. |
| **Spatial Persistence** | • Multi-day Persistent Hotspots (`persistent_location_flag = 1`) | Identifies geographic locations where thermal anomalies recur across multiple days within the same spatial grid. | Enable this toggle to immediately highlight stationary factories and smelters while filtering out transient stubble burns. |
| **Max FRP Slider** | Continuous range: `1.0 MW` to `20.0 MW` (0.5 MW step) | Filters events by radiometric intensity threshold. | Drag slider down to 3 MW to isolate small smoldering burns, or slide up to reveal major energy-intensive fires. |
| **ESA WorldCover** | • Built-up<br>• Cropland<br>• Tree cover<br>• Shrubland<br>• Grassland<br>• Bare / sparse | Filters based on European Space Agency (ESA) 10-meter resolution surface land cover. | Select "Built-up" to observe fires occurring inside artificial/industrial surfaces. |
| **OSM Proximity Relevance** | • Higher Relevance (Metals, Chemical, Power)<br>• Caution Lower Relevance<br>• General Context | Categorizes infrastructure by likelihood of thermal emissions. | Filter for "Higher Relevance" to inspect hotspots located adjacent to known heavy industries. |
| **Sentinel-2 Optical Status** | • Analysis Succeeded (80 events)<br>• Missing Post-Image<br>• Missing Pre-Image<br>• Cloud Rejected<br>• Insufficient Valid Data | Reflects the availability and quality of pre/post optical satellite passes. | Select "Analysis Succeeded" to examine events with full optical vegetation index validation. |

### Active Filter Pills & Reset Controls:
- **Active Pills Bar:** When any filter is activated, an interactive pill bar appears between the KPI bar and map, showing dismissible tags (e.g., `Class: Industrial`, `Multi-day Hotspots Only`). Clicking `×` on any pill removes that single condition; clicking `Clear all` resets the entire view.
- **Sidebar Collapse / Expand:** The collapse toggle button (`◀` / `▶`) collapses the sidebar completely to 36px, hiding all text cleanly without map overlap and expanding the GIS viewport.
- **Zero-Result Recovery:** If a combination of filters yields 0 matches, an informational card appears in the map center offering a single-click "Reset All Filters" button.

---

## 5. Slide-Over Event Detail Drawer

Clicking any event marker slides open an in-depth analytical inspector from the right side of the screen. The drawer organizes all multi-modal evidence into **eight structured sections** in authoritative order:

```
┌─────────────────────────────────────────────────────────────┐
│ 📍 SECTION A: Event Identity (ID, Time, Coords, Sensor)     │
├─────────────────────────────────────────────────────────────┤
│ 🔥 SECTION B: FIRMS Thermal Detection (FRP, Temp, Day/Night)│
├─────────────────────────────────────────────────────────────┤
│ 🧠 SECTION C: ML Prediction & Live FastAPI Microservice     │
├─────────────────────────────────────────────────────────────┤
│ 🏭 SECTION D: OpenStreetMap Industrial Context (Facilities) │
├─────────────────────────────────────────────────────────────┤
│ 🌍 SECTION E: ESA WorldCover Land Cover Context             │
├─────────────────────────────────────────────────────────────┤
│ 🛰️ SECTION F: Sentinel-2 Optical Multi-Spectral Context     │
├─────────────────────────────────────────────────────────────┤
│ 📋 SECTION G: Human Expert Ground Truth                     │
├─────────────────────────────────────────────────────────────┤
│ 🔒 SECTION H: Data Provenance & Audit Trail                 │
└─────────────────────────────────────────────────────────────┘
```

### Section-by-Section Examination:

### Section A: Event Identity (📍)
- **What is shown:** Event ID (e.g., `FIRMS_TN_0000`), Acquisition Date & Time (UTC), Latitude & Longitude (formatted to 4 decimal places), Satellite Platform (e.g., `S-NPP`), Instrument (`VIIRS`), and FIRMS Detection Confidence (`High (h)` / `Nominal (n)` / `Low (l)`).
- **Data Source:** NASA FIRMS raw observation record.
- **Evidence Type:** Primary observational record.

### Section B: FIRMS Thermal Detection (🔥)
- **What is shown:**
  - Fire Radiative Power: Instantaneous energy output in Megawatts (MW).
  - Brightness (I4 Channel, 375m mid-infrared): Radiometric temperature in Kelvin (K).
  - Brightness T31 (I5 Channel, 375m thermal-infrared): Background temperature in Kelvin (K).
  - Day / Night Overpass: Indicates solar illumination (`☀️ Daytime (D)` vs `🌙 Nighttime (N)`).
  - Grid Active Days & Grid Detection Count: Cumulative temporal recurrence in the surrounding spatial cell.
  - Multi-day Persistent Hotspot: Flagged as `● Multi-day Persistent Thermal Source` vs `Transient Anomaly`.
- **Data Source:** VIIRS 375m active fire product and temporal grid aggregator.
- **Evidence Type:** Physical radiometry and temporal persistence measurements.

### Section C: ML Prediction & Live FastAPI Microservice (🧠)
- **Scientific Disclaimer Banner:** *"Prediction is an algorithmic ML estimate. It is not ground truth."*
- **What is shown:**
  - Predicted Class: One of the 3 production classes.
  - Winning Probability: Normalized percentage (e.g., `94.2%`).
  - ML Confidence Tier: `HIGH` ($\ge 75\%$), `MEDIUM` ($50\% - 74\%$), or `LOW` ($< 50\%$).
  - Class Probability Distribution Bars: Visual horizontal bars displaying exact predicted probabilities across all 3 classes simultaneously.
  - **Live FastAPI Microservice Card (`LivePredictionCard`):**
    - A live interactive test button: `⚡ Re-predict via Live FastAPI Service`.
    - Dispatches a real-time HTTP POST request to the local FastAPI inference engine (`/api/v1/predict`) passing the exact 36 engineered features.
    - Measures round-trip execution latency in milliseconds (typically 10–20 ms).
    - Compares live API output against precomputed baseline (`Matches Baseline: Yes`).
    - Displays live model SHA-256 digest and execution timestamp.
- **Evidence Type:** Machine Learning statistical inference.

### Section D: OpenStreetMap Industrial Context (🏭)
- **Scientific Disclaimer Banner:** *"OpenStreetMap (OSM) information provides geographic context and is not ground truth."*
- **What is shown:**
  - Nearest Facility Name: Registered name of neighboring facility (e.g., `Salem Steel Plant`).
  - Facility Type & Category: Classification tags (e.g., `substation`, `industrial`).
  - Facility Relevance Tier: `HIGHER_RELEVANCE` (heavy metallurgy, chemicals, refineries, power generation), `CAUTION_LOWER_RELEVANCE`, or `GENERAL_CONTEXT`.
  - Distance to Nearest Facility: Euclidean distance in meters/kilometers.
  - Distance to High-Relevance Facility: Distance specifically to high-risk industrial units.
  - Nearest High-Relevance Category: Category name of that facility.
  - OSM Coverage Status: Confirms whether spatial tiles were retrieved (`COVERED`) or failed (`FAILED_TILE`).
- **Data Source:** Overpass API / OpenStreetMap spatial database.
- **Evidence Type:** Contextual geospatial infrastructure data.

### Section E: Land Cover Context (🌍)
- **What is shown:** ESA WorldCover Class (e.g., `Built-up`, `Cropland`, `Tree cover`, `Shrubland`) and numeric land cover code (e.g., `50` for Built-up, `40` for Cropland).
- **Data Source:** European Space Agency (ESA) 10-meter WorldCover global product.
- **Evidence Type:** Static surface land-use context.

### Section F: Sentinel-2 Optical Context (🛰️)
- **Scientific Disclaimer Banner:** *"Sentinel-2 provides optical surface and change evidence; it is not a thermal sensor."*
- **What is shown:**
  - Pre-Fire & Post-Fire Observation Status: Confirms cloud-free imagery availability (`REAL_CDSE_SUCCESS`, `CLOUD_REJECTED`, or `MISSING_PRODUCT`).
  - Change Analysis Status: Overall status of bi-temporal pair analysis (`SUCCESS`, `MISSING_POST`, `CLOUD_REJECTED`, etc.).
  - Pre-Fire NDVI Mean & Post-Fire NDVI Mean: Normalized Difference Vegetation Index values before and after the thermal event.
  - NDVI Change (Post - Pre): Difference metric showing loss of green vegetative biomass.
  - Burn Severity (dNBR Mean): Delta Normalized Burn Ratio indicating fire scar severity on the ground.
  - Informational Notice: When optical imagery is unavailable, explains orbital revisit constraints (5-day constellation cycle) and cloud interference, clarifying that lack of optical imagery does not disprove fire occurrence.
- **Data Source:** Copernicus Data Space Ecosystem (CDSE) Sentinel-2 Level-2A optical surface reflectance.
- **Evidence Type:** Optical vegetation change evidence.

### Section G: Human Expert Ground Truth (📋)
- **What is shown:**
  - When validated: Validation status (`VERIFIED`), Validation Certainty (`Unambiguous Ground Truth` vs `Ambiguous / Requires Review`), and Expert Ground-Truth Class.
  - When unvalidated: Clear warning card: *"Not human validated: This thermal event has not undergone independent expert ground-truth validation. Displayed classifications reflect automated ML estimates."*
- **Data Source:** Expert visual inspection of multi-spectral imagery, local news records, and facility cadastral records.
- **Evidence Type:** Ground truth reference benchmark.

### Section H: Data Provenance & Audit Trail (🔒)
- **What is shown:**
  - Model Version: Exact path and identifier (`phase_5_ml_handoff/final_model.joblib`).
  - Model SHA-256 Digest: Cryptographic hash (`5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798`) guaranteeing reproducibility.
  - Data Source Version: Dataset release tag.
  - Inference Timestamp: UTC timestamp when the event prediction was generated.
- **Data Source:** Backend model registry and artifact metadata.
- **Evidence Type:** Audit and regulatory compliance trail.

---

## 6. Machine Learning Model Architecture & Interpretation

### The Three Production Classes:
1. **Industrial Thermal Activity:**
   - Characterized by high thermal persistence, close proximity to industrial zones (e.g., steel rolling mills, thermal power plants, cement kilns, flares), and often built-up or bare surface land cover.
2. **Agricultural Burning:**
   - Characterized by transient (single-day) thermal detections, cropland land cover, low-to-moderate FRP, and seasonal clustering aligned with harvest cycles.
3. **Natural / Wildfire / Other:**
   - Characterized by forest or shrubland land cover, remote locations far from industrial infrastructure, and varying burn intensities.

### Prediction Probabilities & Confidence Scale:
The Random Forest classifier outputs a calibrated probability distribution across all three classes summing to $1.0$ ($100\%$). The winning class corresponds to the maximum probability ($P_{\max}$).

$$\text{Confidence Tier} = \begin{cases} 
\text{HIGH} & \text{if } P_{\max} \ge 0.75 \\
\text{MEDIUM} & \text{if } 0.50 \le P_{\max} < 0.75 \\
\text{LOW} & \text{if } P_{\max} < 0.50 
\end{cases}$$

### Critical Scientific Principle:
> **"ML confidence is not ground truth."**  
> High ML confidence simply means that the engineered feature vector closely resembles training examples. It is a mathematical similarity metric, not physical ground reality or legal liability.

---

## 7. NASA FIRMS Thermal Data Contributions

NASA's **Fire Information for Resource Management System (FIRMS)** delivers near-real-time satellite thermal detections using the **VIIRS (Visible Infrared Imaging Radiometer Suite)** instrument on board the Suomi-NPP and NOAA-20/21 satellites.

### What FIRMS Provides:
- Mid-wave infrared (3.75 $\mu\text{m}$, I4 channel) radiance anomaly detection at 375m nadir resolution.
- Radiative energy release rate (Fire Radiative Power, FRP).
- Exact timestamp and orbital scan geometry.

### Critical Distinction:
> **FIRMS detects thermal anomalies, NOT industrial fires.**  
> FIRMS registers thermal contrast against background terrain. It does not know whether a heat signature originates from a steel blast furnace, a burning sugarcane field, a municipal landfill fire, or a lightning strike. That classification is the unique responsibility of our downstream multi-modal pipeline.

---

## 8. OpenStreetMap (OSM) Infrastructure Context

OpenStreetMap provides vector infrastructure context by calculating spatial distances from the thermal hotspot to nearby registered facilities.

### Facility Relevance Tiers:
- **Higher Relevance:** Metallurgical plants, iron/steel works, chemical factories, oil refineries, cement factories, thermal power generation plants.
- **General Context:** Light industrial estates, commercial warehouses, transport depots.
- **Caution Lower Relevance:** Small workshops, electrical transformers, agricultural storage facilities.

### Critical Distinction:
> **"OpenStreetMap is contextual evidence, not ground truth."**  
> Proximity to an industrial facility does not prove the facility caused the fire. A farmer burning stubble 150 meters outside a factory fence line must not be falsely classified as an industrial emission. The model combines proximity with land cover, persistence, and thermal intensity to make balanced inferences.

---

## 9. ESA WorldCover Land Cover Context

The **European Space Agency (ESA) WorldCover** product provides global land-use maps at 10-meter spatial resolution derived from Sentinel-1 radar and Sentinel-2 optical imagery.

### Role in the System:
- Identifies whether the ground surface beneath the 375m thermal pixel is `Built-up`, `Cropland`, `Tree cover`, or `Grassland`.
- Helps distinguish open-field agricultural burning (which occurs on `Cropland`) from structural industrial fires (which occur on `Built-up` surfaces).

### Limitations:
- WorldCover represents a static annual baseline. It cannot detect intra-annual conversions, temporary fallow land, or small cleared patches within complex industrial plots.

---

## 10. Sentinel-2 Optical Multi-Spectral Change Verification

The **Sentinel-2** mission (Sentinel-2A & Sentinel-2B) provides 13-band optical and shortwave-infrared imagery at 10m to 20m resolution with a 5-day constellation revisit cycle.

### Key Metrics Displayed:
- **Normalized Difference Vegetation Index (NDVI):**
  $$\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}} = \frac{\text{Band 8} - \text{Band 4}}{\text{Band 8} + \text{Band 4}}$$
  Measures live green vegetation density before and after the event. A sharp drop ($\Delta\text{NDVI} < 0$) indicates vegetation loss or harvest clearing.
- **Delta Normalized Burn Ratio (dNBR):**
  $$\text{NBR} = \frac{\text{NIR} - \text{SWIR}}{\text{NIR} + \text{SWIR}} = \frac{\text{Band 8} - \text{Band 12}}{\text{Band 8} + \text{Band 12}}, \quad \text{dNBR} = \text{NBR}_{\text{pre}} - \text{NBR}_{\text{post}}$$
  Quantifies burn severity through charcoal deposition and canopy removal.

### Critical Sensor Distinctions:
> **Sentinel-2 is NOT a thermal sensor.**  
> Sentinel-2 measures reflected solar radiation in optical and near/shortwave infrared bands; it does not measure active thermal emission plumes in mid-wave infrared. Unavailability of optical imagery (e.g., due to cloud cover or orbital revisit intervals) **does not indicate absence of fire activity**.

---

## 11. Spatial & Temporal Persistence

Thermal persistence quantifies whether heat anomalies recur at the exact same geographical coordinate over multiple satellite passes across distinct calendar days.

- **Grid Active Days:** The number of unique calendar days that thermal anomalies were detected within that spatial grid cell.
- **Grid Detection Count:** Total number of raw satellite detections recorded in that cell.
- **Persistent Location Flag:** Set to `1` if the location exhibits repeated multi-day thermal activity.

### Interpretation:
- Continuous industrial manufacturing processes (such as blast furnaces, hot strip mills, glass kilns, and refinery flares) operate continuously throughout the year and routinely trigger persistent thermal flags.
- Stubble burning and wildfires typically flare and extinguish within hours or 1–2 days, appearing as transient anomalies.
- *Caveat:* Multi-day persistence alone does not guarantee an industrial source (e.g., slow-burning peat fires or multi-day agricultural clearing can occasionally persist across several days).

---

## 12. Fire Radiative Power (FRP)

**Fire Radiative Power (FRP)** is the instantaneous rate of radiant heat energy emitted by a fire, measured in Megawatts (MW).

- Calculated by VIIRS using the 3.75 $\mu\text{m}$ mid-infrared radiance contrast over the background surface.
- In the dashboard, FRP directly drives marker circle scaling (larger circle = higher thermal output).
- *Scientific Guardrail:* High FRP does **not** automatically denote an industrial fire. Massive agricultural burns or crown forest fires can produce higher instantaneous FRP (>50 MW) than a well-shielded industrial furnace (5–15 MW).

---

## 13. Map Legend

Located at the bottom right of the map viewport, the expandable Map Legend explains:
- **Tri-Color Code:**
  - 🔴 Crimson: Industrial Thermal Activity
  - 🟠 Amber: Agricultural Burning
  - 🟢 Emerald: Natural / Wildfire / Other
- **Marker Size Indicator:** Clarifies that circle radius scales with FRP in Megawatts.
- **Scientific Guardrail:** Reminds users that markers reflect algorithmic Random Forest predictions, not ground-truth labels.
- **Interactive Control:** Can be minimized (`▼`) to minimize visual obstruction or expanded (`▲`) for full guidance.

---

## 14. Demo Quick Picks

Located in the global header, the **Demo Quick Picks** feature offers judges four pre-configured demonstration benchmarks:

| Quick Pick Button | Target Name | Location / Context | Expected Class | Demo Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `FIRMS_TN_0000` | **Salem Steel (SAIL)** | Salem, TN • Metallurgical Complex | Industrial Thermal Activity | **Primary Industrial Demo:** Shows multi-day persistence, high FRP, proximity to heavy metal facilities, and high ML confidence. |
| `FIRMS_TN_0008` | **JSW Steel (Mecheri)** | Mecheri, TN • Steel Manufacturing | Industrial Thermal Activity | **Secondary Industrial Demo:** Demonstrates industrial facility classification near high-relevance manufacturing clusters. |
| `FIRMS_TN_0001` | **Ramanathapuram** | Ramanathapuram, TN • Agricultural Belt | Agricultural Burning | **Agricultural Contrast Demo:** Shows cropland land cover, transient single-day anomaly, and low-to-moderate FRP. |
| `FIRMS_TN_0004` | **Quarry / Mining** | Mining / Extraction Basin | Agricultural Burning (Edge Case) | **Scientific Edge Case Demo:** High-FRP extraction site illustrating the nuance between open-pit operations and crop burning. |

*Presenter Tip:* When a quick pick is selected, if current active filters hide that event, the dashboard automatically clears filters, displays a yellow notification banner, centers the map on the event, and opens the drawer.

---

## 15. Standard Evaluator Workflow: 6-Step Journey

When demonstrating the system to a hackathon judge or operational stakeholder, follow this standard six-step evaluation sequence:

```
┌───────────┐     ┌───────────┐     ┌───────────┐
│ 1. DETECT │ ──> │ 2. FILTER │ ──> │ 3.INSPECT │
└───────────┘     └───────────┘     └───────────┘
                                          │
                                          ▼
┌───────────┐     ┌───────────┐     ┌───────────┐
│6.VALIDATE │ <── │5.REVIEW ML│ <── │4.EVIDENCE │
└───────────┘     └───────────┘     └───────────┘
```

1. **DETECT:** Begin at the regional view showing all 633 Tamil Nadu thermal events across the state.
2. **FILTER:** Open the sidebar, filter by `Multi-day Persistent Hotspots`, and select `Industrial Thermal Activity`. Watch the KPI bar update instantly to show isolated industrial hotspots.
3. **INSPECT:** Click on `FIRMS_TN_0000` (Salem Steel Plant) from Quick Picks or the map. The map smoothly zooms and centers, and the Event Detail Drawer opens.
4. **EVIDENCE:** Walk the judge through the multi-modal evidence layers:
   - *Thermal:* Check FRP (15.5 MW) and multi-day persistence.
   - *OSM:* Check distance to Salem Steel Plant (<500 meters, Higher Relevance).
   - *Land Cover:* Confirm built-up industrial footprint.
5. **REVIEW ML PREDICTION:** Show the Random Forest probability distribution (>90% Industrial). Click `⚡ Re-predict via Live FastAPI Service` to prove that the live Python backend evaluates the exact 36-feature vector in under 20 ms.
6. **VALIDATE:** Review Section G (Human Expert Ground Truth) to verify independent confirmation, and Section H to inspect the model SHA-256 cryptographic provenance hash.

---

## 16. Summary of Core Scientific Guardrails

To maintain strict scientific and regulatory credibility, the system enforces these foundational guardrails:

```
┌──────────────────────────────┬────────────────────────────────────────────────────────┐
│ Component / Sensor           │ Scientific Role & Guardrail Boundary                   │
├──────────────────────────────┼────────────────────────────────────────────────────────┤
│ NASA FIRMS (VIIRS)           │ Thermal anomaly detection; does NOT classify industry. │
│ OpenStreetMap (OSM)          │ Spatial proximity context; does NOT prove causation.   │
│ ESA WorldCover               │ Static land cover context; does NOT prove fuel source. │
│ Copernicus Sentinel-2        │ Optical surface change; NOT a thermal sensor.          │
│ Random Forest Classifier     │ Multi-modal statistical inference; NOT ground truth.   │
│ Human Ground Truth           │ Independent expert audit benchmark.                    │
└──────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 17. 60–90 Second Elevator Pitch for Judges

*(A ready-to-deliver verbal presentation script for team members addressing Smart India Hackathon evaluators while interacting with the dashboard:)*

> *"Good morning, esteemed judges. Welcome to our **Industrial Fire Detection and Classification System**.*
>
> *Every day, satellite systems like NASA's **Fire Information for Resource Management System (FIRMS)** detect hundreds of thermal anomalies across India. However, existing government systems cannot distinguish between routine agricultural stubble burning and critical industrial factory fires, flares, or explosions.*
>
> *Our platform solves this challenge through **multi-modal evidence fusion**. Instead of relying on a single sensor, we fuse thermal infrared data from NASA satellites, 10-meter land cover classification from the European Space Agency's WorldCover, vector infrastructure data from OpenStreetMap, and optical surface change verification from the Sentinel-2 satellite constellation.*
>
> *Here on the dashboard, you can see all 633 thermal events recorded across Tamil Nadu. Detections are color-coded: red for industrial activity, amber for agricultural burning, and green for natural wildfires. Marker sizes scale proportionally with Fire Radiative Power (FRP).*
>
> *Using our **Demo Quick Picks**, let's inspect the **Salem Steel Plant** (`FIRMS_TN_0000`). Clicking it opens our slide-over analytical drawer. You can see the thermal intensity, multi-day persistence, proximity to high-relevance metallurgical facilities, and our Random Forest model predicting industrial activity with over 90% confidence.*
>
> *Notice that we don't treat ML as a black box: every prediction displays a clear scientific disclaimer, full feature probability breakdowns, and an integrated button to re-evaluate the event live against our production FastAPI backend microservice in just 15 milliseconds.*
>
> *Crucially, we enforce strict scientific guardrails: FIRMS detects heat, OpenStreetMap provides context, Sentinel-2 monitors optical change, and our machine learning provides classification. This gives regulatory authorities an audit-ready, transparent tool for environmental compliance and rapid disaster response. Thank you!"*
