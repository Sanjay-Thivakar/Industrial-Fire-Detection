# AI Industrial Fire & Persistent Thermal Source Detection — Baseline V1

**Smart India Hackathon (SIH) 2026 Solution**  
*AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data*

---

## 1. Problem Overview & Baseline V1 Goals

NASA FIRMS detects high-temperature thermal anomalies globally but cannot reliably distinguish between:
- **Industrial Fires**
- **Persistent Industrial Thermal Sources** (e.g. refineries, power plants, cement kilns, flare stacks)
- **Forest & Natural Fires**
- **Agricultural / Stubble Burning**
- **Other Unclassified Anomalies**

**Baseline V1** establishes a clean, reproducible, and modular machine learning baseline pipeline using NASA FIRMS VIIRS sensor detections, OpenStreetMap industrial facility geospatial context, temporal/diurnal features, and ESA WorldCover land cover sampling.

> **Important Scientific Disclaimer**: Baseline V1 uses **heuristic weak labels** as supervised targets for Random Forest classifier training. Model evaluation metrics (precision, recall, F1 score) measure the classifier's agreement with the heuristic rule engine. They **must not** be claimed as real-world accuracy on physical industrial fires without independent ground-truth validation data.

---

## 2. Memory-Safe Ingestion & Data Architecture

- **Memory-Safe Streaming Ingestion**: To process multi-gigabyte global NASA FIRMS CSV exports without exhausting system RAM, `src/data_ingestion/firms_loader.py` uses `pandas` chunked streaming (`chunk_size: 100000`). Each chunk is validated and geographically pre-filtered using the target state bounding box before accumulating candidate records.
- **Expected Data Directory Structure**:
  ```
  data/raw/firms/
  ├── modis/            # fire_nrt_M-C61_*.csv (disabled by default in Baseline V1)
  ├── viirs_noaa20/     # fire_nrt_J1V-C2_*.csv (Primary)
  └── viirs_snpp/       # fire_nrt_SV-C2_*.csv  (Primary)
  ```
- **Sensor Strategy**: **VIIRS** (375 m spatial resolution across Suomi-NPP, NOAA-20, and NOAA-21) is selected as the primary FIRMS sensor. MODIS (`M-C61`) remains configurable via `config/default_config.yaml` (`include_in_baseline: false`).
- **Geospatial Precision**: All spatial matching is performed in a local metric projected coordinate reference system (**EPSG:32643** UTM Zone 43N for Tamil Nadu). Distances are strictly calculated as **projected planar distances**.
- **Configurable Persistence Window**: Temporal persistence (`grid_active_days`) is calculated using a windowed annual timeframe (`persistence_window_days: 365`), preventing multi-year accumulation false positives.
- **Configurable Grid Observations**: The threshold for utilizing local grid background statistics vs global fallbacks is configurable via `spatial.min_grid_obs: 5`.

---

## 3. Modular Architecture

```
SIH PROJECT/
├── config/
│   └── default_config.yaml         # Complete config parameters (chunk size, CRS, thresholds, model hyperparams)
├── data/
│   ├── raw/                        # FIRMS input files under data/raw/firms/
│   └── cache/                      # Cached state boundary, OSM facilities, and sampled land cover
├── outputs/                        # Output CSVs, GeoJSONs, and interactive HTML GIS map
├── src/
│   ├── config.py                   # Central YAML configuration loader & validator
│   ├── utils/
│   │   ├── logger.py               # Application logging setup
│   │   └── geo_utils.py            # Coordinate transformations, UTM CRS detection, bounding box logic
│   ├── data_ingestion/
│   │   ├── firms_loader.py         # Memory-safe streaming FIRMS CSV parser (VIIRS NPP, N20, N21, MODIS)
│   │   ├── boundary_loader.py      # Administrative state boundary loader & cacher
│   │   └── osm_retriever.py        # Multi-mirror Overpass API loader, facility classifier, and local cacher
│   ├── feature_engineering/
│   │   ├── spatial_features.py     # Metric spatial join & projected planar distance metrics
│   │   ├── temporal_features.py    # Temporal, diurnal, and seasonal indicators
│   │   ├── thermal_features.py     # Thermal metrics, ratio, local grid statistics & windowed persistence
│   │   └── landcover_sampler.py    # ESA WorldCover S3 raster sampler via rasterio
│   ├── labeling/
│   │   └── weak_labeler.py         # Heuristic weak-label generator with landcover fallback
│   ├── models/
│   │   └── train_baseline.py       # Random Forest training with leakage-free train-set median imputation
│   ├── visualization/
│   │   └── map_builder.py          # Interactive Folium map generation
│   └── pipeline.py                 # Main orchestrator pipeline
├── tests/
│   ├── test_firms_loader.py        # Tests for chunked ingestion and bbox pre-filtering
│   ├── test_geo_utils.py           # Unit tests for spatial functions
│   ├── test_feature_engineering.py # Unit tests for thermal/spatial formulas and windowed persistence
│   └── test_weak_labeler.py        # Unit tests for weak-label heuristics
├── run_pipeline.py                 # Standalone CLI runner
├── requirements.txt                # Python package dependencies
└── README.md                       # Documentation
```

---

## 4. Installation & Setup

1. **Clone / Open Workspace**:
   Ensure Python 3.8+ is installed on your environment.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Input Data Placement**:
   Place your NASA FIRMS export files in `data/raw/firms/` (e.g., `data/raw/firms/viirs_noaa20/`, `data/raw/firms/viirs_snpp/`) or specify a custom archive via CLI argument `--zip`.

---

## 5. Execution & Verification

### Running the Baseline Pipeline
To execute the complete end-to-end processing pipeline:
```bash
python run_pipeline.py
```

Optional CLI overrides:
```bash
python run_pipeline.py --config config/default_config.yaml --zip data/raw/my_firms_data.zip
```

### Running Unit Tests
To verify spatial calculations, chunked ingestion, thermal formulas, and weak-label rules:
```bash
python -m pytest tests/ -v
```

---

## 6. Output Artifacts

Running the pipeline populates the `outputs/` directory with:

1. **Classified CSV** (`outputs/TamilNadu_Classified_Fires.csv`):
   Full dataset containing engineered features, weak labels, model predicted classes, and prediction confidence scores.
2. **GeoJSON Spatial Data** (`outputs/TamilNadu_Classified_Fires.geojson`):
   Geospatial point features formatted for GIS software (QGIS, ArcGIS).
3. **Interactive GIS Dashboard Map** (`outputs/TamilNadu_FireMap.html`):
   Standalone HTML interactive map featuring:
   - Color-coded fire detection markers by predicted class.
   - Clickable popups displaying brightness, FRP, land cover, and matched facility distance.
   - OSM Industrial facility marker clusters.
   - Administrative state boundary layer.
