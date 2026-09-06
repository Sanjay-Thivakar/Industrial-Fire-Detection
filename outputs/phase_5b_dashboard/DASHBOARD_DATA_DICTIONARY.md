# DASHBOARD DATA DICTIONARY
## `dashboard_events_633.csv`

**File:** `outputs/phase_5b_dashboard/dashboard_events_633.csv`
**Rows:** 633 | **Columns:** 61
**Build date:** 2026-09-06 | **Model:** `phase_5_ml_handoff/final_model.joblib`

---

## GROUP A — EVENT IDENTITY

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 1 | `event_id` | string | 0% | MASTER | Unique event identifier (FIRMS_TN_0000 … FIRMS_TN_0632). Primary join key across all tables. | Use as record key. Show in detail panel header. |
| 2 | `row_id` | int | 0% | MASTER | Sequential 0-based integer index (0–632). | Use for table row numbering. |
| 3 | `acq_date` | string YYYY-MM-DD | 0% | MASTER | NASA FIRMS acquisition date. | Show on event card. Use for date filters. |
| 4 | `acq_time` | int HHMM | 0% | MASTER | Acquisition time in UTC (HHMM format). | Display as formatted time string. |
| 5 | `acq_datetime` | string ISO 8601 | 0% | MASTER | Combined datetime string (YYYY-MM-DDTHH:MM). | Use for timeline visualisations. |
| 6 | `daynight` | string D/N | 0% | MASTER | D = daytime overpass, N = nighttime overpass. | Show as icon/badge on event card. |

---

## GROUP B — LOCATION

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 7 | `latitude` | float64 (WGS84) | 0% | MASTER | Decimal latitude. Range: Tamil Nadu (~8°–14°N). | Map marker Y coordinate. |
| 8 | `longitude` | float64 (WGS84) | 0% | MASTER | Decimal longitude. Range: Tamil Nadu (~76°–81°E). | Map marker X coordinate. |

---

## GROUP C — FIRMS THERMAL EVIDENCE

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 9 | `satellite` | string | 0% | MASTER | Satellite identifier (e.g., N20, NPP). | Show in event detail. |
| 10 | `instrument` | string | 0% | MASTER | Sensor name (VIIRS or MODIS). | Show in event detail. |
| 11 | `firms_confidence` | string h/n/l | 0% | MASTER | NASA FIRMS detection confidence: h=high, n=nominal, l=low. **Not the same as ml_confidence.** | Show as badge. Tooltip: "NASA FIRMS detection quality". |
| 12 | `frp` | float64 (MW) | 0% | MASTER | Fire Radiative Power in megawatts. Primary thermal intensity signal. | Show on event card. Use for marker size scaling. |
| 13 | `brightness` | float64 (K) | 0% | MASTER | Channel 21/22 brightness temperature in Kelvin. | Show in detail panel. |
| 14 | `bright_t31` | float64 (K) | 0% | MASTER | Channel 31 brightness temperature in Kelvin. Background thermal reference. | Show in detail panel. |
| 15 | `brightness_difference` | float64 | 0% | MASTER | brightness - bright_t31. Thermal anomaly magnitude. | Show in detail panel. |
| 16 | `is_day` | int 0/1 | 0% | MASTER | 1 = daytime detection, 0 = nighttime. | Show as icon. |
| 17 | `is_stubble_burning_season` | int 0/1 | 0% | MASTER | 1 = acquisition within known agricultural burning season for Tamil Nadu. | Show as seasonal context badge. |
| 18 | `grid_detection_count` | int | 0% | MASTER | Number of FIRMS detections at this 0.1° grid cell in the dataset. | Show as "Detection frequency". |
| 19 | `grid_active_days` | int | 0% | MASTER | Number of distinct days with detections at this grid cell. | Show as "Active days". |
| 20 | `persistent_location_flag` | int 0/1 | 0% | MASTER | 1 = location has repeated detections across ≥2 days. Indicator of persistent thermal source. | Show as badge: "Persistent Source". |
| 21 | `grid_total_frp` | float64 (MW) | 0% | MASTER | Cumulative FRP across all detections at this grid cell. | Show in detail panel. |
| 22 | `high_frp_flag_local` | int 0/1 | 0% | MASTER | 1 = FRP exceeds local grid baseline threshold. | Show as anomaly indicator. |
| 23 | `brightness_zscore_local` | float64 | 0% | MASTER | Z-score of brightness relative to local grid baseline. Positive = hotter than local average. | Show with colour scale. |

---

## GROUP D — ML PREDICTION

> ⚠️ **IMPORTANT:** These are probabilistic ML estimates from a model trained on 76 events. Display as "ML Prediction" — never as "Classification" or "Ground Truth". Always show alongside probability values and confidence tier.

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 24 | `predicted_class` | string | 0% | PRED | 3-class prediction: "Agricultural Burning", "Industrial Thermal Activity", or "Natural / Wildfire / Other". | Primary classification label. Use distinct colour per class. |
| 25 | `probability_agricultural_burning` | float64 [0,1] | 0% | PRED | Model probability for Agricultural Burning class. | Show as probability bar. |
| 26 | `probability_industrial_thermal_activity` | float64 [0,1] | 0% | PRED | Model probability for Industrial Thermal Activity class. | Show as probability bar. |
| 27 | `probability_natural_wildfire_other` | float64 [0,1] | 0% | PRED | Model probability for Natural/Wildfire/Other class. | Show as probability bar. |
| 28 | `max_probability` | float64 [0,1] | 0% | PRED | Maximum class probability. Drives confidence tier. | Show as % alongside predicted_class. |
| 29 | `ml_confidence` | string HIGH/MEDIUM/LOW | 0% | PRED (renamed from `confidence.1`) | Model confidence tier. HIGH ≥ 0.75, MEDIUM 0.50–0.74, LOW < 0.50. | Colour-code: HIGH=green, MEDIUM=amber, LOW=red. |

---

## GROUP E — OSM CONTEXT

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 30 | `osm_coverage_status` | string | 0% | MASTER | COVERED = OSM tile retrieved for this area. FAILED_TILE = OSM data retrieval failed. | Show as data-quality indicator. |
| 31 | `nearest_facility_name` | string | **76.9%** | MASTER | Name of the nearest OSM industrial facility. Null when unnamed. | Show as "Unknown" when null. |
| 32 | `nearest_facility_type` | string | 0% | MASTER | OSM facility type tag (e.g., "Other Industrial", "Power Plant"). | Show in OSM context section. |
| 33 | `nearest_facility_category` | string | 0% | MASTER | Curated facility category (e.g., "Mining & Quarry", "Power Plant"). | Show as category badge. |
| 34 | `nearest_facility_tier` | string | 0% | MASTER | HIGHER_RELEVANCE / CAUTION_LOWER_RELEVANCE / GENERAL_CONTEXT. Indicates relevance of nearest facility to industrial fire detection. | Show as tier indicator. |
| 35 | `distance_to_facility_m` | float64 (m) | 0% | MASTER | Distance to nearest OSM industrial facility in metres. | Show formatted (e.g. "328 m"). |
| 36 | `near_industrial_500m` | int 0/1 | 0% | MASTER | 1 = any industrial facility within 500 m. | Use for proximity filter. |
| 37 | `near_industrial_1000m` | int 0/1 | 0% | MASTER | 1 = any industrial facility within 1 km. | Use for proximity filter. |
| 38 | `near_industrial_2000m` | int 0/1 | 0% | MASTER | 1 = any industrial facility within 2 km. | Use for proximity filter. |
| 39 | `nearest_hr_category` | string | 0% | MASTER | Category of the nearest HIGHER_RELEVANCE industrial facility (e.g., "Steel / Metallurgy"). | Show in OSM context section. |
| 40 | `nearest_hr_name` | string | **70.8%** | MASTER | Name of nearest high-relevance facility. Null when unnamed. | Show as "Unknown" when null. |
| 41 | `distance_to_higher_relevance_m` | float64 (m) | 0% | MASTER | Distance to nearest high-relevance industrial facility in metres. | Show formatted. |

---

## GROUP F — WORLDCOVER

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 42 | `landcover_code` | int | 0% | MASTER | ESA WorldCover 2021 land cover class code. | Use for layer filtering. |
| 43 | `landcover_class` | string | 0% | MASTER | ESA WorldCover 2021 land cover label (e.g., "Built-up", "Cropland", "Tree cover"). | Show as land use badge. Use for filtering. |

---

## GROUP G — SENTINEL-2

> ⚠️ Only 80/633 events (12.6%) have successful pre+post change analysis. Dashboard must communicate availability before displaying spectral values.

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 44 | `pre_observation_status` | string | 0% | MASTER | Pre-fire image acquisition status. Values: REAL_CDSE_SUCCESS / CLOUD_REJECTED / MISSING_PRODUCT. | Show as availability badge. |
| 45 | `post_observation_status` | string | 0% | MASTER | Post-fire image acquisition status. Same values. | Show as availability badge. |
| 46 | `s2_change_status` | string | 0% | MASTER | Outcome of pre/post change analysis. SUCCESS (80 events), MISSING_PRE/POST, CLOUD_REJECTED, etc. | Primary S2 availability flag. |
| 47 | `selected_pre_image_date` | string ISO | 31.0% | MASTER | Acquisition date of the selected pre-fire Sentinel-2 image. Null when MISSING_PRODUCT. | Show as "Not acquired" when null. |
| 48 | `selected_post_image_date` | string ISO | 35.2% | MASTER | Acquisition date of the selected post-fire Sentinel-2 image. | Show as "Not acquired" when null. |
| 49 | `s2_pre_feature_status` | string | 31.0% | MASTER | Feature extraction status for pre-fire image (SUCCESS / INSUFFICIENT_DATA). | Show in S2 detail panel. |
| 50 | `s2_post_feature_status` | string | 35.2% | MASTER | Feature extraction status for post-fire image. | Show in S2 detail panel. |
| 51 | `s2_pre_ndvi_mean` | float64 | **40.8%** | MASTER | Mean NDVI from pre-fire Sentinel-2 image. Range typically -1 to 1. | Show as "N/A" when null. |
| 52 | `s2_post_ndvi_mean` | float64 | **42.5%** | MASTER | Mean NDVI from post-fire Sentinel-2 image. | Show as "N/A" when null. |
| 53 | `s2_dnbr_mean` | float64 | **87.4%** | MASTER | Mean delta NBR (post NBR - pre NBR). Negative = vegetation loss / burn scar. Only available when s2_change_status=SUCCESS. | Show as "N/A" when null. Tooltip: "Burn severity index". |

---

## GROUP H — HUMAN VALIDATION

> ⚠️ **CRITICAL:** Human validation is INDEPENDENT evidence available for only 100/633 events (15.8%). Do NOT display human labels as confirmation of ML predictions. Do NOT imply unreviewed events are incorrect predictions.

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 54 | `has_human_validation` | bool | 0% | MASTER | True = this event has a human expert review. | Show "Human Reviewed" badge for True events only. |
| 55 | `human_validation_status` | string | 0% | MASTER | VERIFIED (100 events) or UNREVIEWED (533 events). | Show as review status indicator. |
| 56 | `human_ground_truth_class` | string | **84.2%** | MASTER | Raw human-assigned label. Uses different class vocabulary than ML classes. Values: Agricultural Burning, Persistent Industrial Thermal Source, Natural/Forest Fire, Industrial Fire, REVIEW_REQUIRED, Other/Unclassified. Null for unreviewed events. | Show as "Not reviewed" when null. Do not remap to ML classes. Display alongside ML prediction, not as a replacement. |
| 57 | `is_unambiguous_ground_truth` | bool | 0% | MASTER | True = human reviewer assigned a clear, confident label (76 events). | Use to flag high-confidence ground truth. |

---

## GROUP I — PROVENANCE

| # | Field | Type | Null% | Source | Description | Display Guidance |
|---|-------|------|-------|--------|-------------|-----------------|
| 58 | `inference_timestamp` | string ISO UTC | 0% | PRED | UTC timestamp of the ML inference run that produced predictions. | Show in "About" or metadata panel. |
| 59 | `model_version` | string | 0% | PRED | Model artifact identifier: `phase_5_ml_handoff/final_model.joblib`. | Show in metadata panel. |
| 60 | `model_sha256` | string | 0% | PRED | SHA-256 hash of the model file used. Enables reproducibility verification. | Show in metadata/audit panel. |
| 61 | `data_source_version` | string | 0% | Derived | Constant: `phase_4b_ground_truth_v1`. Identifies source dataset version. | Show in metadata panel. |

---

## MISSING-VALUE HANDLING SUMMARY

| Field | Null Rate | Frontend Treatment |
|-------|-----------|--------------------|
| `nearest_facility_name` | 76.9% | Display `"Unknown"` |
| `nearest_hr_name` | 70.8% | Display `"Unknown"` |
| `human_ground_truth_class` | 84.2% | Display `"Not reviewed"` |
| `s2_dnbr_mean` | 87.4% | Display `"N/A"` with tooltip |
| `s2_pre_ndvi_mean` | 40.8% | Display `"N/A"` |
| `s2_post_ndvi_mean` | 42.5% | Display `"N/A"` |
| `selected_pre_image_date` | 31.0% | Display `"Not acquired"` |
| `selected_post_image_date` | 35.2% | Display `"Not acquired"` |
| `s2_pre_feature_status` | 31.0% | Display `"N/A"` |
| `s2_post_feature_status` | 35.2% | Display `"N/A"` |
| All ML prediction fields | **0%** | Always present |
| All identity/location fields | **0%** | Always present |

---

*Data dictionary for `dashboard_events_633.csv` — Phase 5B Step 2*
