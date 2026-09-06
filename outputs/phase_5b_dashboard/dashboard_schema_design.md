# PHASE 5B — DASHBOARD DATA SCHEMA DESIGN

**Document Status:** Design only — no files created or modified.
**Audit basis:** Phase 5A PASS (predictions_633.csv, 633 rows, all checks passed)
**Author:** Phase 5B automated schema design
**Date:** 2026-09-06

---

## SOURCE FILES INSPECTED (READ-ONLY)

| Alias | Path | Rows | Cols |
|-------|------|------|------|
| `PRED` | `outputs/phase_5a_inference_633/predictions_633.csv` | 633 | 30 |
| `MASTER` | `outputs/phase_4b_ground_truth/sentinel2_master_633_human_ground_truth.csv` | 633 | 177 |
| `S2FULL` | `outputs/sentinel2_full_633/sentinel2_full_633_events.csv` | 633 | 165 |
| `ENRICHED` | `outputs/ground_truth_investigation/firms_spatially_enriched_v2.csv` | 633 | 43 |
| `MODEL_META` | `outputs/phase_5_ml_handoff/final_model_metadata.json` | — | — |

> **Key finding:** `S2FULL` has zero columns not already present in `MASTER`. `ENRICHED` adds only `distance_to_general_context_m`, `scan`, `track`, `version` — none useful for dashboard. The authoritative join source for dashboard construction is **`MASTER`** (left join) **+ `PRED`** (right join on `event_id`).

---

## RECOMMENDED FINAL SCHEMA

**Total fields: 61** across 9 logical groups.

```
GROUP A  — Event Identity         (6 fields)
GROUP B  — Location               (2 fields)
GROUP C  — FIRMS Thermal Evidence (15 fields)
GROUP D  — ML Prediction          (6 fields)
GROUP E  — OSM Context            (12 fields)
GROUP F  — WorldCover             (2 fields)
GROUP G  — Sentinel-2             (10 fields)
GROUP H  — Human Validation       (4 fields)
GROUP I  — Provenance             (4 fields)
```

---

## FIELD-BY-FIELD DATA DICTIONARY

### GROUP A — EVENT IDENTITY

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 1 | `event_id` | MASTER | `event_id` | str | 0% | ✅ Required | ✅ Yes |
| 2 | `row_id` | MASTER | `row_id` | int | 0% | ✅ Required | ✅ Yes |
| 3 | `acq_date` | MASTER | `acq_date` | str (YYYY-MM-DD) | 0% | ✅ Required | ✅ Yes |
| 4 | `acq_time` | MASTER | `acq_time` | int (HHMM) | 0% | Optional | ✅ Yes |
| 5 | `acq_datetime` | MASTER | `acq_datetime` | str (ISO) | 0% | Optional | ✅ Yes |
| 6 | `daynight` | MASTER | `daynight` | str (D/N) | 0% | Optional | ✅ Yes |

**Purpose:** Primary event identifiers and acquisition timestamps. `event_id` is the join key across all tables.

---

### GROUP B — LOCATION

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 7 | `latitude` | MASTER | `latitude` | float64 | 0% | ✅ Required | ✅ Yes |
| 8 | `longitude` | MASTER | `longitude` | float64 | 0% | ✅ Required | ✅ Yes |

**Purpose:** Map rendering. Both are zero-null and unchanged from the verified source.

---

### GROUP C — FIRMS THERMAL EVIDENCE

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 9 | `satellite` | MASTER | `satellite` | str | 0% | Optional | ✅ Yes |
| 10 | `instrument` | MASTER | `instrument` | str | 0% | Optional | ✅ Yes |
| 11 | `firms_confidence` | MASTER | `confidence` | str (h/n/l) | 0% | ✅ Required | ✅ Yes |
| 12 | `frp` | MASTER | `frp` | float64 (MW) | 0% | ✅ Required | ✅ Yes |
| 13 | `brightness` | MASTER | `brightness` | float64 (K) | 0% | Optional | ✅ Yes |
| 14 | `bright_t31` | MASTER | `bright_t31` | float64 (K) | 0% | Optional | ✅ Yes |
| 15 | `brightness_difference` | MASTER | `brightness_difference` | float64 | 0% | Optional | ✅ Yes |
| 16 | `is_day` | MASTER | `is_day` | int (0/1) | 0% | Optional | ✅ Yes |
| 17 | `is_stubble_burning_season` | MASTER | `is_stubble_burning_season` | int (0/1) | 0% | Optional | ✅ Yes |
| 18 | `grid_detection_count` | MASTER | `grid_detection_count` | int | 0% | Optional | ✅ Yes |
| 19 | `grid_active_days` | MASTER | `grid_active_days` | int | 0% | Optional | ✅ Yes |
| 20 | `persistent_location_flag` | MASTER | `persistent_location_flag` | int (0/1) | 0% | Optional | ✅ Yes |
| 21 | `grid_total_frp` | MASTER | `grid_total_frp` | float64 | 0% | Optional | ✅ Yes |
| 22 | `high_frp_flag_local` | MASTER | `high_frp_flag_local` | int (0/1) | 0% | Optional | ✅ Yes |
| 23 | `brightness_zscore_local` | MASTER | `brightness_zscore_local` | float64 | 0% | Optional | ✅ Yes |

**Purpose:** Core thermal signal quality indicators used by the ML model. `firms_confidence` is renamed from source `confidence` to avoid collision with `ml_confidence`. `frp` is the primary intensity signal for dashboard cards.

---

### GROUP D — ML PREDICTION

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 24 | `predicted_class` | PRED | `predicted_class` | str | 0% | ✅ Required | ✅ Yes |
| 25 | `probability_agricultural_burning` | PRED | `probability_agricultural_burning` | float64 | 0% | ✅ Required | ✅ Yes |
| 26 | `probability_industrial_thermal_activity` | PRED | `probability_industrial_thermal_activity` | float64 | 0% | ✅ Required | ✅ Yes |
| 27 | `probability_natural_wildfire_other` | PRED | `probability_natural_wildfire_other` | float64 | 0% | ✅ Required | ✅ Yes |
| 28 | `max_probability` | PRED | `max_probability` | float64 | 0% | ✅ Required | ✅ Yes |
| 29 | `ml_confidence` | PRED | `confidence.1` | str (HIGH/MEDIUM/LOW) | 0% | ✅ Required | ✅ Yes |

**Renaming required:**
- `confidence.1` → `ml_confidence` (pandas auto-rename artifact, must be fixed)

**Purpose:** Primary ML output for dashboard classification display. The 3 probabilities enable probability bar charts. `ml_confidence` drives colour coding (HIGH = green, MEDIUM = amber, LOW = red).

> ⚠️ **SCIENTIFIC CAUTION:** `predicted_class` is a probabilistic ML estimate. It must NOT be displayed as ground truth. The dashboard must label it clearly as "ML Prediction" — never "Classification" or "Label" without qualification.

---

### GROUP E — OSM CONTEXT

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 30 | `osm_coverage_status` | MASTER | `osm_coverage_status` | str | 0% | ✅ Required | ✅ Yes |
| 31 | `nearest_facility_name` | MASTER | `nearest_facility_name` | str | **76.9%** | Optional | ✅ Yes |
| 32 | `nearest_facility_type` | MASTER | `nearest_facility_type` | str | 0% | Optional | ✅ Yes |
| 33 | `nearest_facility_category` | MASTER | `nearest_facility_category` | str | 0% | Optional | ✅ Yes |
| 34 | `nearest_facility_tier` | MASTER | `nearest_facility_tier` | str | 0% | Optional | ✅ Yes |
| 35 | `distance_to_facility_m` | MASTER | `distance_to_facility_m` | float64 | 0% | ✅ Required | ✅ Yes |
| 36 | `near_industrial_500m` | MASTER | `near_industrial_500m` | int (0/1) | 0% | Optional | ✅ Yes |
| 37 | `near_industrial_1000m` | MASTER | `near_industrial_1000m` | int (0/1) | 0% | Optional | ✅ Yes |
| 38 | `near_industrial_2000m` | MASTER | `near_industrial_2000m` | int (0/1) | 0% | Optional | ✅ Yes |
| 39 | `nearest_hr_category` | MASTER | `nearest_hr_category` | str | 0% | Optional | ✅ Yes |
| 40 | `nearest_hr_name` | MASTER | `nearest_hr_name` | str | **70.8%** | Optional | ✅ Yes |
| 41 | `distance_to_higher_relevance_m` | MASTER | `distance_to_higher_relevance_m` | float64 | 0% | Optional | ✅ Yes |

**Purpose:** Spatial industrial context for map tooltips. `nearest_facility_name` and `nearest_hr_name` are high-null (76.9% / 70.8%) — display as "Unknown" when null. Tier and category fields drive industrial proximity indicators on the dashboard.

**Notable OSM coverage:** `osm_coverage_status` is 0% null. Values: `COVERED` (325 events, 51.3%), `FAILED_TILE` (308 events, 48.7%).

---

### GROUP F — WORLDCOVER

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 42 | `landcover_code` | MASTER | `landcover_code` | int | 0% | ✅ Required | ✅ Yes |
| 43 | `landcover_class` | MASTER | `landcover_class` | str | 0% | ✅ Required | ✅ Yes |

**Purpose:** ESA WorldCover 2021 land surface type. Used for dashboard map colour layers and event context. Zero nulls.

**Observed distribution:** Built-up (24.5%), Tree cover (21.2%), Cropland (21.0%), Grassland (18.2%), Shrubland (10.9%), Bare/sparse vegetation (3.8%), others (0.5%).

---

### GROUP G — SENTINEL-2

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 44 | `pre_observation_status` | MASTER | `pre_observation_status` | str | 0% | ✅ Required | ✅ Yes |
| 45 | `post_observation_status` | MASTER | `post_observation_status` | str | 0% | ✅ Required | ✅ Yes |
| 46 | `s2_change_status` | MASTER | `s2_change_status` | str | 0% | ✅ Required | ✅ Yes |
| 47 | `selected_pre_image_date` | MASTER | `selected_pre_image_date` | str (ISO) | **31.0%** | Optional | ✅ Yes |
| 48 | `selected_post_image_date` | MASTER | `selected_post_image_date` | str (ISO) | **35.2%** | Optional | ✅ Yes |
| 49 | `s2_pre_feature_status` | MASTER | `s2_pre_feature_status` | str | 31.0% | Optional | ✅ Yes |
| 50 | `s2_post_feature_status` | MASTER | `s2_post_feature_status` | str | 35.2% | Optional | ✅ Yes |
| 51 | `s2_pre_ndvi_mean` | MASTER | `s2_pre_ndvi_mean` | float64 | **40.8%** | Optional | ✅ Yes |
| 52 | `s2_post_ndvi_mean` | MASTER | `s2_post_ndvi_mean` | float64 | **42.5%** | Optional | ✅ Yes |
| 53 | `s2_dnbr_mean` | MASTER | `s2_dnbr_mean` | float64 | **87.4%** | Optional | ✅ Yes |

**Purpose:** Sentinel-2 availability and change indicators. The 3 status fields (`pre_observation_status`, `post_observation_status`, `s2_change_status`) are 0% null and essential for showing data availability on the dashboard. Spectral values (NDVI, dNBR) are high-null due to cloud rejection and missing products — expose only where available; dashboard must handle nulls gracefully.

**S2 observation status observed values:**
- `pre_observation_status`: CLOUD_REJECTED (233), REAL_CDSE_SUCCESS (204), MISSING_PRODUCT (196)
- `post_observation_status`: CLOUD_REJECTED (225), MISSING_PRODUCT (223), REAL_CDSE_SUCCESS (185)
- `s2_change_status`: MISSING_POST (169), MISSING_PRE (158), INSUFFICIENT_VALID_DATA (126), SUCCESS (80), INVALID_INPUT (70), MISSING_BOTH (30)

---

### GROUP H — HUMAN VALIDATION

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 54 | `has_human_validation` | MASTER | `has_human_validation` | bool | 0% | ✅ Required | ✅ Yes |
| 55 | `human_validation_status` | MASTER | `human_validation_status` | str | 0% | ✅ Required | ✅ Yes |
| 56 | `human_ground_truth_class` | MASTER | `human_ground_truth_class` | str | **84.2%** | Optional | ⚠️ With caveat |
| 57 | `is_unambiguous_ground_truth` | MASTER | `is_unambiguous_ground_truth` | bool | 0% | Optional | ⚠️ With caveat |

**Fields intentionally omitted from Group H dashboard exposure:**
- `human_review_confidence` — 99.7% null, not useful
- `human_validation_notes` — 100% null (not collected)
- `human_raw_label` — pre-normalization raw string, exposes internal label schema to users
- `human_industry_observation` — 92.1% null, present/absent classification too sparse
- `ml_training_eligible` — internal pipeline field, not user-relevant

**Purpose:** Shows which events have independent human review. Must be displayed with strict separation from ML predictions.

> ⚠️ **CRITICAL SCIENTIFIC CAUTION:**
>
> `human_ground_truth_class` is available for only **100 of 633 events (15.8%)** and contains internal classes (`REVIEW_REQUIRED`, `Persistent Industrial Thermal Source`) that do not map 1:1 to the 3 ML production classes. The dashboard must:
> - Never display `human_ground_truth_class` as if it validates or overrides `predicted_class`.
> - Clearly label validated events as "Human Reviewed" with a distinct badge/indicator.
> - Show `human_ground_truth_class` as "Not reviewed" / null-safe for the 84.2% unreviewed events.
> - Never imply that the absence of a human label means the ML prediction is incorrect.

---

### GROUP I — PROVENANCE

| # | Dashboard Field | Source File | Source Column | Type | Null? | Required | Frontend Safe |
|---|----------------|-------------|---------------|------|-------|----------|---------------|
| 58 | `inference_timestamp` | PRED | `inference_timestamp` | str (ISO UTC) | 0% | ✅ Required | ✅ Yes |
| 59 | `model_version` | PRED | `model_version` | str | 0% | ✅ Required | ✅ Yes |
| 60 | `model_sha256` | PRED | `model_sha256` | str | 0% | Optional | ✅ Yes |
| 61 | `data_source_version` | MASTER | *(derived)* | str | — | Optional | ✅ Yes |

**Note:** `data_source_version` should be set to the literal string `"phase_4b_ground_truth_v1"` since no version column exists in the source — it is a derived constant applied at dashboard CSV construction time.

`model_path` from PRED is redundant with `model_version` and is excluded from the dashboard export (internal path).

---

## SOURCE MAPPING SUMMARY

| Dashboard Group | Primary Source | Join Key |
|-----------------|---------------|----------|
| A — Identity | MASTER | `event_id` |
| B — Location | MASTER | `event_id` |
| C — FIRMS Thermal | MASTER | `event_id` |
| D — ML Prediction | PRED | `event_id` |
| E — OSM Context | MASTER | `event_id` |
| F — WorldCover | MASTER | `event_id` |
| G — Sentinel-2 | MASTER | `event_id` |
| H — Human Validation | MASTER | `event_id` |
| I — Provenance | PRED (+ derived) | `event_id` |

**Join strategy:** Left join MASTER on `event_id` → PRED on `event_id`. Both have exactly 633 rows and identical `event_id` sets. No fanout or loss expected.

---

## MISSING-DATA BEHAVIOR

| Field | Null Rate | Dashboard Treatment |
|-------|-----------|---------------------|
| `nearest_facility_name` | 76.9% | Display as `"Unknown"` |
| `nearest_hr_name` | 70.8% | Display as `"Unknown"` |
| `human_ground_truth_class` | 84.2% | Display as `"Not reviewed"` |
| `s2_dnbr_mean` | 87.4% | Display as `"N/A"` with tooltip explanation |
| `s2_pre_ndvi_mean` | 40.8% | Display as `"N/A"` — link to `pre_observation_status` |
| `s2_post_ndvi_mean` | 42.5% | Display as `"N/A"` — link to `post_observation_status` |
| `selected_pre_image_date` | 31.0% | Display as `"Not acquired"` |
| `selected_post_image_date` | 35.2% | Display as `"Not acquired"` |
| All ML prediction fields | 0% | Always present — no null handling needed |
| All identity/location fields | 0% | Always present |
| All OSM tier/category fields | 0% | Always present |

---

## SCIENTIFIC / UX CAUTIONS

### 1. ML Prediction ≠ Ground Truth
`predicted_class` is a probabilistic ML output from a model trained on **76 labeled events**. It must be displayed with its probability and confidence tier, not as a definitive label.

### 2. Human Validation Coverage is 15.8%
Only 100 of 633 events were human-reviewed. The dashboard must clearly communicate this scope limitation. Do not display a "validated" badge on the other 533.

### 3. `human_ground_truth_class` Uses Different Label Schema
The raw human labels (`Persistent Industrial Thermal Source`, `Industrial Fire`, `Natural/Forest Fire`) do not map 1:1 to the 3 production ML classes. The dashboard should display the raw label with a footnote. No automated remapping should be done without a documented mapping table.

### 4. Sentinel-2 Data is Highly Incomplete
Only 80 of 633 events (12.6%) have `s2_change_status = SUCCESS`. Cloud rejection is the dominant cause. The dashboard must not imply S2 change analysis was possible for all events.

### 5. OSM Coverage Gaps
48.7% of events are in `FAILED_TILE` zones for OSM coverage. Proximity metrics are still computed from global OSM, but confidence in nearby-facility detection is lower in these zones.

### 6. FIRMS confidence vs. ML confidence
`firms_confidence` (h/n/l) is a NASA FIRMS quality flag. `ml_confidence` (HIGH/MEDIUM/LOW) is a model probability tier. They measure completely different things and must never be conflated.

### 7. Predicted Class Distribution Warning
The model predicts `Industrial Thermal Activity` at 41.2% of all 633 events — substantially higher than the 19.8% share in the 76-event training set. This is not a model error; it reflects that the full 633-event population includes many events near OSM industrial facilities not represented in the training labels. This asymmetry should be noted in dashboard documentation.

---

## EXAMPLE DASHBOARD RECORD

Shown as key-value for event `FIRMS_TN_0000`:

```json
{
  "event_id": "FIRMS_TN_0000",
  "row_id": 0,
  "acq_date": "2024-11-01",
  "acq_time": 1940,
  "acq_datetime": "2024-11-01T19:00",
  "daynight": "N",
  "latitude": 11.65394,
  "longitude": 78.02792,
  "satellite": "N20",
  "instrument": "VIIRS",
  "firms_confidence": "n",
  "frp": 1.16,
  "brightness": 311.10,
  "bright_t31": 287.43,
  "brightness_difference": 23.67,
  "is_day": 0,
  "is_stubble_burning_season": 1,
  "grid_detection_count": 2,
  "grid_active_days": 1,
  "persistent_location_flag": 0,
  "grid_total_frp": 2.46,
  "high_frp_flag_local": 0,
  "brightness_zscore_local": -0.4622,
  "predicted_class": "Industrial Thermal Activity",
  "probability_agricultural_burning": 0.4331,
  "probability_industrial_thermal_activity": 0.5031,
  "probability_natural_wildfire_other": 0.0639,
  "max_probability": 0.5031,
  "ml_confidence": "MEDIUM",
  "osm_coverage_status": "COVERED",
  "nearest_facility_name": null,
  "nearest_facility_type": "Other Industrial",
  "nearest_facility_category": "Substation & Electrical Infrastructure",
  "nearest_facility_tier": "CAUTION_LOWER_RELEVANCE",
  "distance_to_facility_m": 328.33,
  "near_industrial_500m": 1,
  "near_industrial_1000m": 1,
  "near_industrial_2000m": 1,
  "nearest_hr_category": "Steel / Metallurgy",
  "nearest_hr_name": "Salem Steel Plant",
  "distance_to_higher_relevance_m": 458.27,
  "landcover_code": 50,
  "landcover_class": "Built-up",
  "pre_observation_status": "REAL_CDSE_SUCCESS",
  "post_observation_status": "MISSING_PRODUCT",
  "s2_change_status": "MISSING_POST",
  "selected_pre_image_date": "2024-10-29T05:08:39Z",
  "selected_post_image_date": null,
  "s2_pre_feature_status": "SUCCESS",
  "s2_post_feature_status": null,
  "s2_pre_ndvi_mean": 0.6201,
  "s2_post_ndvi_mean": null,
  "s2_dnbr_mean": null,
  "has_human_validation": false,
  "human_validation_status": "UNREVIEWED",
  "human_ground_truth_class": null,
  "is_unambiguous_ground_truth": false,
  "inference_timestamp": "2026-09-06T17:19:14Z",
  "model_version": "phase_5_ml_handoff/final_model.joblib",
  "model_sha256": "5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798",
  "data_source_version": "phase_4b_ground_truth_v1"
}
```

---

## FIELDS INTENTIONALLY EXCLUDED

### A. Internal pipeline / intermediate fields
| Excluded Field | Source Column | Reason |
|----------------|--------------|--------|
| `model_path` | `PRED.model_path` | Absolute local path — exposes filesystem; redundant with `model_version` |
| `is_spatial_duplicate` | `MASTER` | Internal deduplication flag, not user-relevant |
| `selection_rationale` | `MASTER` | Internal candidate selection notes |
| `candidate_priority_score` | `MASTER` | Raw numeric score — superseded by `candidate_priority` categorical |
| `candidate_priority` | `MASTER` | Internal pipeline priority tier, not dashboard-relevant |
| `ml_training_eligible` | `MASTER` | Internal training pipeline flag |
| `cv_fold_5` | `MASTER` | Cross-validation fold assignment |
| `weak_label` | `MASTER` | Heuristic label used in training preparation — NOT ground truth; could confuse users |
| `ground_truth_status` | `MASTER` | Internal labeling status string |

### B. Redundant / duplicate fields
| Excluded Field | Reason |
|----------------|--------|
| `distance_to_facility_km` | Duplicate of `distance_to_facility_m` in km — retain only metres |
| `distance_to_higher_relevance_km` | Duplicate in km — retain only metres |
| `near_industrial_5000m` | Retain 500m/1km/2km flags; 5km/10km have low discriminative value at dashboard level |
| `near_industrial_10000m` | Same |
| `near_higher_relevance_500m` to `near_higher_relevance_10000m` | Boolean proximity flags covered by `distance_to_higher_relevance_m` |
| `frp_brightness_ratio` | Derived intermediate — not directly interpretable for end users |
| `log_frp` | Log-transformed version of `frp` — expose raw `frp` only |
| `confidence_numeric` | Numeric encoding of FIRMS `confidence` — expose string only |
| `grid_brightness_mean` | Collinear with `brightness` and `brightness_zscore_local` |
| `high_brightness_flag_local` | Superseded by `brightness_zscore_local` |
| `grid_frp_mean`, `grid_frp_std`, `grid_n` | Grid statistics not in master; raw aggregates not needed |
| `frp_zscore_local` | Collinear with `high_frp_flag_local` and `frp`; too technical for dashboard |

### C. Raw Sentinel-2 arrays / redundant S2 fields
| Excluded Field | Reason |
|----------------|--------|
| `s2_pre_ndvi_min/max/std/median` | Raw statistical detail; retain only mean |
| `s2_post_ndvi_min/max/std/median` | Same |
| `s2_pre_nbr_min/max/std/median` | Same |
| `s2_post_nbr_min/max/std/median` | Same |
| `s2_pre_ndwi_*`, `s2_post_ndwi_*` | NDWI not directly relevant to fire classification display |
| `s2_pre_swir_ratio_*`, `s2_post_swir_ratio_*` | Too technical; retain dNBR for burn signal |
| `s2_pre_b04_mean` etc. (raw band means) | Raw reflectance — not interpretable by end users |
| `s2_dndvi_median`, `s2_abs_dndvi_mean/median` | Retain only `s2_dnbr_mean` as the primary change indicator |
| `s2_dndwi_*`, `s2_dswir_ratio_*` | Not dashboard-relevant |
| `pre_bbox_wgs84`, `post_bbox_wgs84` | WKT bounding boxes — dashboard uses point coordinates |
| `pre_download_bytes`, `post_download_bytes` | Internal download size; not user-relevant |
| `pre_product_id`, `post_product_id` | CDSE internal IDs |
| `pre_product_name`, `post_product_name` | CDSE product names — too technical |
| `pre_tile_id`, `post_tile_id` | Sentinel-2 tile grid reference |
| `pre_cloud_cover_catalogue`, `post_cloud_cover_catalogue` | Catalogue-level cloud % — superseded by observation status |
| `pre_raster_dimensions`, `post_raster_dimensions` | Pixel dimensions — internal |
| `pre_bands_requested`, `post_bands_requested` | Band list — internal |
| `s2_pre_total_pixels`, `s2_post_total_pixels` | Pixel counts — internal |
| `s2_pre_spectral_valid_pixels`, `s2_pre_spectral_valid_pct` | Internal QA metrics |
| `s2_post_spectral_valid_pixels`, `s2_post_spectral_valid_pct` | Internal QA metrics |
| `raster_dimensions_px`, `bands_requested`, `aoi_dimensions_m` | Processing parameters |
| `processing_timestamp`, `error_category` | Internal pipeline metadata |
| `failure_reason`, `processing_status`, `is_real_cdse_data` | Internal acquisition pipeline flags |

### D. Sensitive / leakage-risk fields
| Excluded Field | Reason |
|----------------|--------|
| `human_raw_label` | Pre-normalization string exposes internal labeling conventions |
| `human_review_confidence` | 99.7% null, not useful |
| `human_validation_notes` | 100% null |
| `human_industry_observation` | 92.1% null; inconsistent values (`"Present "` with trailing space) |
| `normalization_notes` | Internal normalization log |
| `is_forest_fire_season` | Seasonal flag — collinear with `acq_date` and `is_stubble_burning_season` |

### E. Enriched-only fields with no join key
| Excluded Field | Source | Reason |
|----------------|--------|--------|
| `distance_to_general_context_m` | ENRICHED | No `event_id` in ENRICHED — cannot join reliably |
| `scan`, `track`, `version` | ENRICHED | FIRMS scan/track geometry and version — not dashboard-relevant |

---

## RENAME MAP

| Current Column (source) | Dashboard Name | Location |
|-------------------------|---------------|----------|
| `confidence` (MASTER) | `firms_confidence` | Group C |
| `confidence.1` (PRED) | `ml_confidence` | Group D |
| `nearest_hr_osm_id` | *(excluded)* | — |
| `nearest_facility_osm_id` | *(excluded)* | — |
| `nearest_facility_osm_type` | *(excluded)* | — |

---

## CONSTRUCTION PLAN (next step)

1. Load `MASTER` (633 rows × 177 cols) and `PRED` (633 rows × 30 cols)
2. Join on `event_id` (inner join — identical sets, safe)
3. Select exactly the 57 dashboard fields listed above
4. Rename `confidence` → `firms_confidence`, `confidence.1` → `ml_confidence`
5. Add derived constant: `data_source_version = "phase_4b_ground_truth_v1"`
6. Write to: `outputs/phase_5b_dashboard/dashboard_events_633.csv`
7. Validate: 633 rows, 57+ cols, zero nulls in required fields, no leakage fields

---

*Schema design document — read-only phase. No files created or modified.*
*Next: PHASE 5B STEP 2 — Build dashboard_events_633.csv*
