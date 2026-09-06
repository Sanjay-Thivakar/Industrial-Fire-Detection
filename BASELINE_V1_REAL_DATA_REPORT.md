# BASELINE V1 REAL DATA EXECUTION & ANALYSIS REPORT
**Phase**: Phase 2A — Real Data Baseline Execution & Analysis  
**Project**: AI-Based Detection and Classification of Industrial Fires (SIH 2026)  
**Target Region**: Tamil Nadu, India  
**Date**: September 1, 2026  
**Lead Auditor**: Antigravity AI Pair Programmer  

---

## 1. Executive Summary

Phase 2A executed the audited **Baseline V1** pipeline on the complete real NASA FIRMS dataset present in `data/raw/firms/` (6,581,026 raw VIIRS records across 284 MB NOAA-20 and 244 MB Suomi-NPP files). 

The technical execution was clean and memory-safe: streaming chunked ingestion completed in 17 seconds using < 50 MB RAM, geographic bounding-box pre-filtering extracted 1,256 candidates, and state polygon containment identified **633 real thermal detection events** inside Tamil Nadu between November 1, 2024 and January 12, 2025.

However, empirical analysis of the real data reveals a critical scientific bottleneck: **0 of the 633 real fire detections fell within 2,000 meters of an OSM industrial facility** (the minimum matched distance was 2.58 km). As a direct result of the 2,000m threshold in the weak-labeling rules, **0 events were labeled as "Industrial Fire" or "Persistent Thermal Source"**, leaving 92.58% of events as "Other/Unclassified" and 7.42% as Agricultural Burning.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 2A EMPIRICAL FINDINGS                         │
├─────────────────────────┬───────────────────────┬───────────────────────┤
│ Memory & Technical Run  │ Distance to OSM       │ Weak Label Breakdown  │
│                         │ Nearest Facility      │                       │
├─────────────────────────┼───────────────────────┼───────────────────────┤
│ Status: SUCCESS         │ Min: 2.58 km          │ Industrial Fire: 0    │
│ Streamed 6.58M rows in  │ Median: 68.64 km      │ Persistent Source: 0  │
│ 17s using <50MB RAM.    │ 0 events <= 2.0 km    │ Forest Fire: 0        │
│ 633 TN detections.      │ (100% > 2.0 km)       │ Ag Burning: 47 (7.4%) │
│                         │                       │ Unclassified: 586     │
└─────────────────────────┴───────────────────────┴───────────────────────┘
```

---

## 2. Input Data Inventory

A thorough inspection of `data/raw/firms/` was performed prior to execution. The raw dataset contains 3 CSV files totaling 576.16 MB and 7,312,164 global records:

| File Name | Path | Size (MB) | Sensor / Product | Columns | Row Count | Date Range | Latitude Range | Longitude Range |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `fire_nrt_J1V-C2_565335.csv` | `data/raw/firms/viirs_noaa20/` | 271.59 MB | VIIRS NOAA-20 (`J1V-C2`) | 14 | 3,419,726 | 2024-11-01 to 2025-01-13 | [-63.8857, 76.6663] | [-176.1338, 179.6038] |
| `fire_nrt_SV-C2_565336.csv` | `data/raw/firms/viirs_snpp/` | 244.75 MB | VIIRS Suomi-NPP (`SV-C2`) | 14 | 3,161,300 | 2024-11-01 to 2025-01-13 | [-53.8041, 78.7354] | [-179.8305, 179.5940] |
| `fire_nrt_M-C61_565334.csv` | `data/raw/firms/modis/` | 59.82 MB | MODIS (`M-C61`) | 14 | 731,138 | 2024-11-01 to 2025-01-13 | [-53.2141, 66.7758] | [-176.4831, 179.5399] |

### Sensor Configuration Verification:
- **Primary Sensors**: VIIRS NOAA-20 (`J1V-C2`) and VIIRS Suomi-NPP (`SV-C2`) enabled (6,581,026 primary rows).
- **Secondary Sensors**: MODIS (`M-C61`) correctly disabled by default (`include_in_baseline: false`).

---

## 3. FIRMS Ingestion Statistics

Memory-safe chunked streaming ingestion (`chunk_size: 100000`) processed the global datasets in real-time:

- **Files Processed**: 2 CSV files
- **Chunks Processed**: 67 chunks
- **Total Source Rows Encountered**: 6,581,026 rows
- **Rows Surviving Coordinate Validation**: 6,581,026 rows (0 invalid coordinate rows)
- **Rows Surviving Bounding Box Pre-Filter (TN BBox `[76.23, 8.08, 80.35, 13.54]`)**: 1,256 rows
- **Final Tamil Nadu Polygon Detections**: **633 rows**
- **Deduplicated Rows Removed**: 0 rows

---

## 4. Sensor Distribution

Distribution of the 633 Tamil Nadu fire detections across primary VIIRS sensors:

| Sensor / Satellite Source | Detection Count | Percentage (%) |
| :--- | :--- | :--- |
| **VIIRS NOAA-20** (`VIIRS_N20`) | 341 | 53.87% |
| **VIIRS Suomi-NPP** (`VIIRS_SUOMI_NPP`) | 292 | 46.13% |
| **VIIRS NOAA-21** (`VIIRS_NOAA21`) | 0 | 0.00% (File not in raw dir) |
| **MODIS** (`MODIS`) | 0 | 0.00% (Disabled in config) |
| **Total** | **633** | **100.00%** |

---

## 5. Temporal Distribution

The input dataset spans approximately 2.5 winter months (November 1, 2024 to January 12, 2025):

### Monthly Breakdown:
- **January 2025**: 255 detections (40.28%)
- **December 2024**: 238 detections (37.60%)
- **November 2024**: 140 detections (22.12%)

### Diurnal (Day/Night) Breakdown:
- **Nighttime Detections (`N`)**: 377 detections (59.56%)
- **Daytime Detections (`D`)**: 256 detections (40.44%)

---

## 6. OSM Industrial Context Statistics

OSM facility matching reprojected coordinates into **EPSG:32643** (UTM Zone 43N) and calculated projected planar distances to 25 parsed industrial facilities:

### Distance to Nearest Facility Statistics:
- **Minimum Distance**: **2.5799 km** (2,579.9 meters)
- **25th Percentile**: 40.12 km
- **Median Distance**: 68.64 km
- **Mean Distance**: 81.94 km
- **75th Percentile**: 122.42 km
- **90th Percentile**: 151.35 km
- **Maximum Distance**: 296.90 km

### Proximity Radii Breakdown:
- **Detections <= 500 meters**: **0 (0.00%)**
- **Detections <= 1,000 meters**: **0 (0.00%)**
- **Detections <= 2,000 meters**: **0 (0.00%)**
- **Detections <= 5,000 meters**: **2 (0.32%)**
- **Detections > 2,000 meters**: **633 (100.00%)**

### Nearest Matched Facility Types:
- Warehouse/Depot: 212 (33.49%)
- Power Plant: 140 (22.12%)
- Chemical: 133 (21.01%)
- Oil & Gas: 101 (15.96%)
- Industrial Works: 33 (5.21%)
- Manufacturing: 14 (2.21%)

---

## 7. WorldCover Land-Cover Distribution

Land-cover sampling via rasterio S3 range-read produced:

| ESA WorldCover Class | Code | Count | Percentage (%) |
| :--- | :---: | :---: | :---: |
| **Unknown (Unsampled / Fallback)** | NaN | 487 | 76.94% |
| **Cropland** | 40 | 72 | 11.37% |
| **Tree cover** | 10 | 50 | 7.90% |
| **Shrubland** | 20 | 12 | 1.90% |
| **Grassland** | 30 | 10 | 1.58% |
| **Permanent water bodies** | 80 | 1 | 0.16% |
| **Built-up** | 50 | 1 | 0.16% |
| **Total** | | **633** | **100.00%** |

*Note*: 487 detections fell outside the 4 fetched GeoTIFF tiles or returned HTTP range fallbacks, resulting in `Unknown` land cover for 76.94% of detections.

---

## 8. Thermal Feature Statistics

Statistical summary of thermal variables across 633 detections:

| Feature Name | Min | Median | Mean | 75th Pct | 90th Pct | Max | Missing |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`brightness` (K)** | 295.60 | 310.97 | 318.23 | 332.77 | 338.28 | 367.00 | 0 |
| **`bright_t31` (K)** | 266.66 | 292.23 | 292.75 | 297.22 | 300.91 | 307.18 | 0 |
| **`frp` (MW)** | 0.18 | 1.53 | 2.32 | 3.00 | 4.69 | 16.84 | 0 |
| **`brightness_difference` (K)** | 10.02 | 22.87 | 25.48 | 34.93 | 40.40 | 73.35 | 0 |
| **`frp_brightness_ratio`** | 0.0006 | 0.0048 | 0.0070 | 0.0090 | 0.0142 | 0.0495 | 0 |
| **`log_frp`** | 0.17 | 0.93 | 1.04 | 1.39 | 1.74 | 2.88 | 0 |
| **`brightness_zscore_local`** | -2.36 | 0.53 | 0.29 | 1.01 | 1.39 | 3.17 | 0 |
| **`frp_zscore_local`** | -2.04 | -0.02 | 0.17 | 0.62 | 1.44 | 5.63 | 0 |

---

## 9. Temporal & Persistence Feature Statistics

- **`grid_active_days`**: Min = 1, Median = 1.0, Mean = 4.22, 75th = 6.0, Max = 20
- **`persistent_location_flag` (>=3 active days)**: 272 detections (42.97%) flagged as persistent location; 361 detections (57.03%) non-persistent.
- **`is_forest_fire_season` (months 2,3,4,5)**: 0 (0.00%) — the dataset spans Nov–Jan.
- **`is_stubble_burning_season` (months 4,5,10,11)**: 140 (22.12%) in November.

---

## 10. Complete 31-Feature Inventory

All 31 model features required by Baseline V1 were generated and verified:

| # | Feature Name | Category | Primary Source | Missing Count | Min | Median | Mean | Max |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `brightness` | FIRMS/thermal | NASA FIRMS | 0 | 295.60 | 310.97 | 318.23 | 367.00 |
| 2 | `bright_t31` | FIRMS/thermal | NASA FIRMS | 0 | 266.66 | 292.23 | 292.75 | 307.18 |
| 3 | `frp` | FIRMS/thermal | NASA FIRMS | 0 | 0.18 | 1.53 | 2.32 | 16.84 |
| 4 | `scan` | FIRMS/sensor geometry | NASA FIRMS | 0 | 0.32 | 0.42 | 0.44 | 0.79 |
| 5 | `track` | FIRMS/sensor geometry | NASA FIRMS | 0 | 0.36 | 0.41 | 0.45 | 0.78 |
| 6 | `brightness_difference` | FIRMS/thermal ratio | NASA FIRMS | 0 | 10.02 | 22.87 | 25.48 | 73.35 |
| 7 | `frp_brightness_ratio` | FIRMS/thermal ratio | NASA FIRMS | 0 | 0.0006 | 0.0048 | 0.0070 | 0.0495 |
| 8 | `log_frp` | FIRMS/thermal ratio | NASA FIRMS | 0 | 0.17 | 0.93 | 1.04 | 2.88 |
| 9 | `confidence_numeric` | FIRMS/quality | NASA FIRMS | 0 | 0.00 | 1.00 | 1.00 | 2.00 |
| 10 | `is_n20` | FIRMS/sensor source | NASA FIRMS | 0 | 0.00 | 1.00 | 0.54 | 1.00 |
| 11 | `is_suomi_npp` | FIRMS/sensor source | NASA FIRMS | 0 | 0.00 | 0.00 | 0.46 | 1.00 |
| 12 | `is_day` | Temporal/diurnal | Derived | 0 | 0.00 | 0.00 | 0.40 | 1.00 |
| 13 | `hour` | Temporal/diurnal | Derived | 0 | 7.00 | 19.00 | 14.85 | 21.00 |
| 14 | `month` | Temporal/calendar | Derived | 0 | 1.00 | 11.00 | 7.35 | 12.00 |
| 15 | `day_of_year` | Temporal/calendar | Derived | 0 | 1.00 | 314.00 | 204.50 | 366.00 |
| 16 | `distance_to_facility_km` | Spatial/OSM distance | OSM | 0 | 2.58 | 68.64 | 81.94 | 296.90 |
| 17 | `industrial_facility_present` | Spatial/OSM indicator | OSM | 0 | 1.00 | 1.00 | 1.00 | 1.00 |
| 18 | `facility_type_code` | Spatial/OSM category | OSM | 0 | 1.00 | 4.00 | 4.74 | 9.00 |
| 19 | `near_industrial_500m` | Spatial/OSM proximity | OSM | 0 | 0.00 | 0.00 | 0.00 | 0.00 |
| 20 | `near_industrial_1000m` | Spatial/OSM proximity | OSM | 0 | 0.00 | 0.00 | 0.00 | 0.00 |
| 21 | `near_industrial_2000m` | Spatial/OSM proximity | OSM | 0 | 0.00 | 0.00 | 0.00 | 0.00 |
| 22 | `near_industrial_5000m` | Spatial/OSM proximity | OSM | 0 | 0.00 | 0.00 | 0.0032 | 1.00 |
| 23 | `grid_detection_count` | Grid/spatial density | Derived | 0 | 1.00 | 2.00 | 9.30 | 43.00 |
| 24 | `grid_active_days` | Grid/temporal persistence| Derived | 0 | 1.00 | 1.00 | 4.22 | 20.00 |
| 25 | `grid_total_frp` | Grid/thermal accumulation| Derived | 0 | 0.21 | 6.70 | 14.51 | 64.30 |
| 26 | `brightness_zscore_local` | Grid/thermal z-score | Derived | 0 | -2.36 | 0.53 | 0.29 | 3.17 |
| 27 | `frp_zscore_local` | Grid/thermal z-score | Derived | 0 | -2.04 | -0.02 | 0.17 | 5.63 |
| 28 | `used_local_baseline` | Grid/quality indicator | Derived | 0 | 0.00 | 0.00 | 0.45 | 1.00 |
| 29 | `is_forest_fire_season` | Temporal/seasonal window | Derived | 0 | 0.00 | 0.00 | 0.00 | 0.00 |
| 30 | `is_stubble_burning_season`| Temporal/seasonal window | Derived | 0 | 0.00 | 0.00 | 0.22 | 1.00 |
| 31 | `landcover_code` | Land-cover/ESA WorldCover| WorldCover | 487 | 10.00 | 40.00 | 27.74 | 80.00 |

---

## 11. Weak-Label Class Distribution

Class breakdown generated by `src/labeling/weak_labeler.py`:

| Target Class | Heuristic Rule Trigger | Count | Percentage (%) |
| :--- | :--- | :---: | :---: |
| **Industrial Fire** | Near facility <= 2km & Local Thermal Spike | **0** | **0.00%** |
| **Persistent Thermal Source** | Near facility <= 2km & Persistent Active Days >= 3 | **0** | **0.00%** |
| **Forest Fire** | Tree cover & Not near facility & Forest Season | **0** | **0.00%** |
| **Agricultural Burning** | Cropland & Not persistent & Stubble Season (Nov) | **18** | **2.84%** |
| **Possible Agricultural Burning**| Fallback: Not near facility & Not persistent & Stubble Season (Nov) | **29** | **4.58%** |
| **Other/Unclassified** | Default fallback for all remaining events | **586** | **92.58%** |
| **Total** | | **633** | **100.00%** |

### Key Diagnostic Discovery:
Because zero fire detections in this 2.5-month real dataset fell within 2,000 meters of an OSM facility, the heuristic rules **could not assign a single detection to Industrial Fire or Persistent Thermal Source**.

---

## 12. Random Forest Baseline Performance

- **Train Set**: 474 rows (75%)
- **Test Set**: 159 rows (25%)
- **Classes in Training Set**: 3 (`Other/Unclassified`, `Possible Agricultural Burning`, `Agricultural Burning`)
- **Imputation**: `train_medians = X_train.median()` fit strictly on `X_train` (Imputed median `landcover_code = 40.0` [Cropland]).

### Held-out Test Set Classification Report:

```
                               precision    recall  f1-score   support

         Agricultural Burning       0.62      1.00      0.77         5
           Other/Unclassified       1.00      0.98      0.99       147
Possible Agricultural Burning       1.00      1.00      1.00         7

                     accuracy                           0.98       159
                    macro avg       0.88      0.99      0.92       159
                 weighted avg       0.99      0.98      0.98       159
```

> **Important Scientific Label**: These metrics measure **WEAK-LABEL BASELINE PERFORMANCE** (the classifier's ability to emulate the heuristic rule engine). They do **NOT** represent ground-truth real-world accuracy on physical fires.

---

## 13. Confusion Matrix

Held-out test set confusion matrix (Rows = Actual Weak Label, Columns = Predicted Class):

```
                                Predicted:    Predicted:              Predicted:
                                Ag Burning    Other/Unclassified     Possible Ag Burning
Actual: Ag Burning                  5             0                          0
Actual: Other/Unclassified          3           144                          0
Actual: Possible Ag Burning         0             0                          7
```

---

## 14. Feature Importance

Top 10 Gini feature importances extracted from the fitted Random Forest classifier:

1. **`landcover_code`**: 17.48%
2. **`is_stubble_burning_season`**: 17.17%
3. **`is_suomi_npp`**: 12.56%
4. **`is_n20`**: 11.55%
5. **`month`**: 6.98%
6. **`day_of_year`**: 6.78%
7. **`grid_active_days`**: 3.84%
8. **`grid_detection_count`**: 3.51%
9. **`grid_total_frp`**: 2.99%
10. **`brightness_difference`**: 2.72%

---

## 15. Data Leakage Diagnostic

1. **Train/Test Contamination (CLEAN)**: Missing values in `landcover_code` are imputed using `train_medians = X_train.median()` fit exclusively on `X_train`. No test set statistics polluted model training.
2. **Weak-Label Tautology (PRESENT BY DESIGN)**: The top 2 features (`landcover_code` and `is_stubble_burning_season`) are the exact logical inputs used by `weak_labeler.py` to define the `Agricultural Burning` class. The 98% accuracy reflects near-perfect rule reproduction.
3. **Spatial/Temporal Feature Calculation**: `grid_active_days` uses annual windowing.

---

## 16. Spatial Sanity Check

- **Polygon Containment**: All 633 final FIRMS points are 100% strictly within the Tamil Nadu state polygon boundary.
- **Geographic Bounds**: Latitudes range from 8.10° N to 13.52° N; longitudes range from 76.35° E to 80.32° E.
- **Spatial Clusters**: Detections cluster around agricultural belts in the Kaveri delta and inland forest/hill tracts.

---

## 17. Output Artifact Verification

- **CSV File** (`outputs/TamilNadu_Classified_Fires.csv`): Exists, 633 rows, 44 columns, contains `predicted_class` and `predicted_class_confidence`.
- **GeoJSON File** (`outputs/TamilNadu_Classified_Fires.geojson`): Exists, 633 valid point features, `EPSG:4326` CRS.
- **Interactive GIS Map** (`outputs/TamilNadu_FireMap.html`): Exists, 841.77 KB, opens successfully with Folium feature layers and popup metrics.

---

## 18. Problems & Warnings Discovered

1. **Zero Industrial Matches at 2,000m**: 0 of 633 real detections fell within 2 km of an OSM facility (minimum matched distance: 2.58 km). The current 2,000m threshold in `weak_labeler.py` produces 0 industrial labels on this dataset.
2. **High WorldCover Missing Rate (76.94%)**: 487 of 633 detections returned `Unknown` land cover, falling back to non-landcover weak-label rules.
3. **Domination of `Other/Unclassified`**: 92.58% of events were lumped into `Other/Unclassified`.

---

## 19. Scientific Interpretation

- **Engineering Correctness**: The pipeline software architecture executed flawlessly. Memory-safe ingestion, spatial joins, raster sampling, weak labeling, model training, and GIS exporting completed without crashes or memory bloat.
- **Scientific Validity**: The current weak-label rules fail to identify industrial thermal sources on this 2.5-month dataset because the 2,000m facility distance threshold is too restrictive for OSM facility coverage in Tamil Nadu. The 98% F1 score represents rule fitting rather than ground-truth physical validation.

---

## 20. Recommended Next Phase

Proceed to **Phase 2B: Weak-Label Heuristic Refinement & Ground Truth Curation**:
1. Evaluate expanding OSM facility search tags (e.g. `landuse=industrial`, `industrial=*`) or adjusting facility proximity thresholds.
2. Curate independent ground-truth industrial fire labels from state fire department logs or news reports.
3. Improve ESA WorldCover tile coverage for rural Tamil Nadu coordinates.

---

## FINAL SUMMARY

OVERALL BASELINE STATUS:
**TECHNICALLY HEALTHY WITH CONCERNS**

DATASET SIZE:
**6,581,026 raw VIIRS records** (516 MB raw CSVs)

TAMIL NADU EVENTS:
**633 confirmed polygon detections**

WEAK-LABEL CLASSES:

| Class | Count | Percentage (%) |
| :--- | :---: | :---: |
| Other/Unclassified | 586 | 92.58% |
| Possible Agricultural Burning | 29 | 4.58% |
| Agricultural Burning | 18 | 2.84% |
| Industrial Fire | 0 | 0.00% |
| Persistent Thermal Source | 0 | 0.00% |

MODEL PERFORMANCE:
- **Accuracy**: 0.98 (98%)
- **Macro F1**: 0.92
- **Weighted F1**: 0.98

TOP 10 FEATURES:
1. `landcover_code` (17.48%)
2. `is_stubble_burning_season` (17.17%)
3. `is_suomi_npp` (12.56%)
4. `is_n20` (11.55%)
5. `month` (6.98%)
6. `day_of_year` (6.78%)
7. `grid_active_days` (3.84%)
8. `grid_detection_count` (3.51%)
9. `grid_total_frp` (2.99%)
10. `brightness_difference` (2.72%)

MOST IMPORTANT DISCOVERED PROBLEM:
0 out of 633 real fire detections fell within 2,000 meters of an OSM facility (min distance: 2.58 km), causing 0 industrial labels to be assigned.

MOST IMPORTANT SCIENTIFIC LIMITATION:
Model metrics evaluate rule emulation against heuristic weak labels, not ground-truth physical fire validation.

RECOMMENDED NEXT ACTION:
Proceed to Phase 2B to review weak-label proximity rules and curate independent ground-truth industrial fire validation data.
