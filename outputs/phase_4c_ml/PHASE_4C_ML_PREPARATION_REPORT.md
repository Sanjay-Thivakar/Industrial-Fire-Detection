# Phase 4C: Final 3-Class ML Feature Preparation Report

**Execution Timestamp:** 2026-09-06 08:17:02Z  
**Source Dataset:** `outputs/phase_4b_ground_truth/ml_labelled_dataset.csv`  
**Source SHA256 Checksum:** `7f446811a4941444ee9a972ad1b469acb759b4089c2ac5a2f0ce9725c0ce1f46`  
**Dataset Scope:** Exactly **76 usable human-validated events** (zero synthetic or heuristic labels)  
**Status:** COMPLETED — ML Feature Pipeline & Cross-Validation Strategy Fully Frozen  

---

## 1. Executive Summary

Phase 4C establishes the definitive machine learning feature representations and evaluation architecture for the project's supervised modeling phase.

Following the statistical audit in Phase 4B, which demonstrated that a 6-class model with classes of size 2 and 3 is statistically non-viable, the supervised classification target has been formulated as a **3-Class Hierarchy**:
1. **Industrial Thermal Activity** (**15 records**, 19.7%)
2. **Agricultural Burning** (**50 records**, 65.8%)
3. **Natural / Wildfire / Other** (**11 records**, 14.5%)

Two frozen feature configurations were constructed to rigorously benchmark the incremental value of satellite optical/SWIR data:
- **Configuration A (Baseline):** **36 features** derived from NASA FIRMS thermal intensity, FIRMS temporal persistence, OpenStreetMap industrial proximity, and ESA WorldCover land cover.
- **Configuration B (Sentinel-2 Enhanced):** **73 features** containing the complete Baseline suite plus **37 Sentinel-2 L2A features** (pre/post spectral indices, SWIR thermal band ratios, dNBR burn severity changes, and physical missingness indicators).

---

## 2. 3-Class Target Formulation & Distribution

The original 6-class human annotations are preserved intact in `human_ground_truth_class`, and mapped into `ml_target_3class`:

| Original Human Ground-Truth Class | Count | Normalized 3-Class Target | 3-Class Count | % of ML Dataset |
| :--- | :---: | :--- | :---: | :---: |
| `Industrial Fire` | 3 | **Industrial Thermal Activity** | **15** | **19.7%** |
| `Persistent Industrial Thermal Source` | 12 | **Industrial Thermal Activity** | | |
| `Agricultural Burning` | 50 | **Agricultural Burning** | **50** | **65.8%** |
| `Natural/Forest Fire` | 9 | **Natural / Wildfire / Other** | **11** | **14.5%** |
| `Other/Unclassified` | 2 | **Natural / Wildfire / Other** | | |
| **Total** | **76** | | **76** | **100.0%** |

### Statistical Properties of the 3-Class Target:
- **Smallest Class:** `Natural / Wildfire / Other` (11 samples, 14.5%)
- **Middle Class:** `Industrial Thermal Activity` (15 samples, 19.7%)
- **Largest Class:** `Agricultural Burning` (50 samples, 65.8%)
- **Effective Imbalance Ratio:** **4.55 : 1** (reduced from the intractable 25 : 1 ratio of the 6-class scheme).
- **Stratified CV Viability:** With 11 and 15 samples, a 5-fold stratified cross-validation scheme guarantees at least 2 test samples for the smallest class and 3 test samples for the industrial class in every validation fold.

---

## 3. Feature Configurations & Manifest Summary

### 3.1 Configuration A — Baseline (36 Features)
The baseline represents information available purely from satellite thermal detection (VIIRS), historical spatial clustering, and GIS layers:
- **FIRMS Thermal Intensity (8 features):** `frp`, `brightness`, `bright_t31`, `brightness_difference`, `frp_brightness_ratio`, `log_frp`, `confidence_numeric`, `is_day`.
- **FIRMS Temporal Persistence (10 features):** `grid_detection_count`, `grid_active_days`, `persistent_location_flag`, `grid_total_frp`, `grid_brightness_mean`, `high_brightness_flag_local`, `high_frp_flag_local`, `brightness_zscore_local`, `frp_zscore_local`, `is_stubble_burning_season`.
- **ESA WorldCover Land Cover (1 feature):** `landcover_code` (10, 20, 30, 40, 50, 60).
- **OpenStreetMap Spatial Proximity (17 features):** `distance_to_facility_m`, `nearest_facility_type`, `nearest_facility_category`, `nearest_facility_tier`, `near_industrial_500m`, `near_industrial_1000m`, `near_industrial_2000m`, `near_industrial_5000m`, `near_industrial_10000m`, `distance_to_higher_relevance_m`, `nearest_hr_category`, `near_higher_relevance_500m`, `near_higher_relevance_1000m`, `near_higher_relevance_2000m`, `near_higher_relevance_5000m`, `near_higher_relevance_10000m`, `osm_coverage_status`.

*Missingness in Baseline:* **0% missing values across all 36 features.**

### 3.2 Configuration B — Sentinel-2 Enhanced (73 Features)
Combines all 36 Baseline features with **37 Sentinel-2 features**:
- **Pre-Event Spectral Indices & Reflectance (13 features):** `s2_pre_ndvi_mean`, `s2_pre_ndvi_std`, `s2_pre_nbr_mean`, `s2_pre_nbr_std`, `s2_pre_ndwi_mean`, `s2_pre_ndwi_std`, `s2_pre_swir_ratio_mean`, `s2_pre_swir_ratio_std`, `s2_pre_b04_mean`, `s2_pre_b08_mean`, `s2_pre_b11_mean`, `s2_pre_b12_mean`, `s2_pre_spectral_valid_pct`.
- **Post-Event Spectral Indices & Reflectance (13 features):** `s2_post_ndvi_mean`, `s2_post_ndvi_std`, `s2_post_nbr_mean`, `s2_post_nbr_std`, `s2_post_ndwi_mean`, `s2_post_ndwi_std`, `s2_post_swir_ratio_mean`, `s2_post_swir_ratio_std`, `s2_post_b04_mean`, `s2_post_b08_mean`, `s2_post_b11_mean`, `s2_post_b12_mean`, `s2_post_spectral_valid_pct`.
- **Dual-Window Temporal Change / Delta Metrics (8 features):** `s2_dndvi_mean`, `s2_abs_dndvi_mean`, `s2_dnbr_mean`, `s2_abs_dnbr_mean`, `s2_dndwi_mean`, `s2_abs_dndwi_mean`, `s2_dswir_ratio_mean`, `s2_abs_dswir_ratio_mean`.
- **Physical Missingness Indicators (3 features):** `s2_pre_missing`, `s2_post_missing`, `s2_change_missing`.

---

## 4. Sentinel-2 Missingness Strategy

### Physical Root Cause of Missingness:
Sentinel-2 values are missing not at random (MNAR), but due to physical atmospheric conditions and satellite orbit mechanics:
1. **Cloud / Shadow Cover (`CLOUD_REJECTED`):** 35.5% of pre-event and 46.1% of post-event windows were obscured by clouds or cloud shadows detected by the Scene Classification Layer (SCL).
2. **Catalogue Search Absence (`MISSING_PRODUCT`):** 23.7% pre and 40.8% post events had no Sentinel-2 overpass within the ±5 day temporal query window.
3. **Dual-Window Delta Requirements:** Delta change features (`s2_dndvi_mean`, `s2_dnbr_mean`) require valid optical rasters for *both* windows; consequently, change features are missing in 85.5% of records.

### Methodological Rules Enforced:
1. **NO Zero Imputation:** Replacing missing NDVI, NBR, or SWIR reflectance with zero is physically disastrous (e.g. NDVI=0 indicates bare rock/water; NBR=0 indicates neutral unburned vegetation; B12=0 indicates total photon absorption).
2. **Missingness Indicators:** Explicit binary flags (`s2_pre_missing`, `s2_post_missing`, `s2_change_missing`) are provided so tree-based models can exploit seasonal or regional cloud patterns without distorting continuous feature spaces.
3. **Strict In-Fold Median Imputation:** For continuous features, missing values are imputed using median values computed **strictly on training fold partitions** (`SimpleImputer(strategy='median')`), ensuring zero information leakage into validation folds.

---

## 5. Target Leakage & Column Exclusion Audit

A strict audit was performed across all 177 columns in the input dataset. The following **104 columns were formally excluded** from model feature spaces:

| Excluded Column | Leakage Category | Audit Reason |
| :--- | :--- | :--- |
| `event_id` | **Identifier / Text Metadata** | Unique event IDs, OSM IDs, or high-cardinality unstructured facility names |
| `row_id` | **Identifier / Text Metadata** | Unique event IDs, OSM IDs, or high-cardinality unstructured facility names |
| `instrument` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `is_forest_fire_season` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `distance_to_facility_km` | **Collinear Duplicate** | Exact linear duplicate of distance_to_facility_m (divided by 1000) |
| `nearest_facility_osm_id` | **Identifier / Text Metadata** | Unique event IDs, OSM IDs, or high-cardinality unstructured facility names |
| `nearest_facility_name` | **Identifier / Text Metadata** | Unique event IDs, OSM IDs, or high-cardinality unstructured facility names |
| `distance_to_higher_relevance_km` | **Collinear Duplicate** | Exact linear duplicate of distance_to_facility_m (divided by 1000) |
| `nearest_hr_osm_id` | **Identifier / Text Metadata** | Unique event IDs, OSM IDs, or high-cardinality unstructured facility names |
| `nearest_hr_name` | **Identifier / Text Metadata** | Unique event IDs, OSM IDs, or high-cardinality unstructured facility names |
| `candidate_priority_score` | **Candidate Selection Metadata** | Engineered during Phase 2C batch curation; contains heuristic priority rules |
| `candidate_priority` | **Candidate Selection Metadata** | Engineered during Phase 2C batch curation; contains heuristic priority rules |
| `is_spatial_duplicate` | **Candidate Selection Metadata** | Engineered during Phase 2C batch curation; contains heuristic priority rules |
| `selection_rationale` | **Candidate Selection Metadata** | Engineered during Phase 2C batch curation; contains heuristic priority rules |
| `ground_truth_status` | **Historical Heuristic Label** | Synthetic rule label or validation state that would bias or leak target |
| `weak_label` | **Historical Heuristic Label** | Synthetic rule label or validation state that would bias or leak target |
| `processing_status` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `is_real_cdse_data` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `failure_reason` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `aoi_dimensions_m` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `raster_dimensions_px` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `bands_requested` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `selected_pre_image_date` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_product_id` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_product_name` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_tile_id` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_observation_status` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_observation_failure_reason` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `selected_post_image_date` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_product_id` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_product_name` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_tile_id` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_observation_status` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_observation_failure_reason` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_obs_date` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_raster_dimensions` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `pre_bands_requested` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `s2_pre_feature_status` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_bbox_wgs84` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `pre_download_bytes` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_obs_date` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_raster_dimensions` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `post_bands_requested` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `s2_post_feature_status` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `s2_pre_total_pixels` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `s2_post_total_pixels` | **Zero-Variance Constant** | Constant across all instances in the dataset |
| `s2_change_status` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `s2_change_failure_reason` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `processing_timestamp` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `error_category` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_bbox_wgs84` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `post_download_bytes` | **Pipeline Runtime Metadata** | Copernicus API product hashes, timestamps, and pipeline debug status strings |
| `in_validation_batch_100` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `has_human_validation` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `human_ground_truth_class` | **Direct Target Variable** | Defines or encodes the ground-truth prediction target |
| `human_validation_confidence` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `human_validation_status` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `human_validation_notes` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `human_raw_label` | **Direct Target Variable** | Defines or encodes the ground-truth prediction target |
| `is_unambiguous_ground_truth` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `human_review_confidence` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `human_industry_observation` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `normalization_notes` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `ml_training_eligible` | **Human Review Metadata** | Created during ground-truth validation process; unavailable at live inference |
| `ml_target_3class` | **Direct Target Variable** | Defines or encodes the ground-truth prediction target |

---

## 6. Reproducible Evaluation Architecture

### 5-Fold Stratified Cross-Validation Splits (`cv_fold_5`):
To ensure 100% fair and reproducible comparison between Baseline and Sentinel-2 Enhanced models, the exact same 5 stratified folds (`random_state=42`) were computed and persisted into `ml_3class_dataset.csv`:

|   cv_fold_5 |   Agricultural Burning |   Industrial Thermal Activity |   Natural / Wildfire / Other |
|------------:|-----------------------:|------------------------------:|-----------------------------:|
|           0 |                     10 |                             3 |                            3 |
|           1 |                     10 |                             3 |                            2 |
|           2 |                     10 |                             3 |                            2 |
|           3 |                     10 |                             3 |                            2 |
|           4 |                     10 |                             3 |                            2 |

- Every fold contains exactly **3 Industrial**, **10 Agricultural**, and **2 to 3 Natural/Other** test samples.
- Every training set contains **12 Industrial**, **40 Agricultural**, and **8 to 9 Natural/Other** training samples.

### Primary Metrics for Model Evaluation:
1. **Macro F1 Score (Primary Selection Metric):** Gives equal weight to Industrial Thermal Activity (19.7%), Natural/Other (14.5%), and Agricultural Burning (65.8%).
2. **Balanced Accuracy:** Average of recall across all three classes.
3. **Per-Class Precision & Recall:** Critical for industrial fire detection to evaluate false alarm rates vs detection rates.
4. **Confusion Matrix:** Evaluates exact error migration (e.g. whether industrial sources are confused with agricultural stubble).
5. **Accuracy (Secondary Metric only):** Retained for completeness, noting that a naive 65.8% majority classifier baseline exists.

---

## 7. Artifact Manifest

1. **Prepared 3-Class Dataset:**  
   `outputs/phase_4c_ml/ml_3class_dataset.csv` (76 rows, includes `ml_target_3class`, `cv_fold_5`, all features, and missingness indicators).
2. **Baseline Feature Manifest:**  
   `outputs/phase_4c_ml/feature_manifest_baseline.csv` (36 features).
3. **Sentinel-2 Enhanced Feature Manifest:**  
   `outputs/phase_4c_ml/feature_manifest_sentinel2.csv` (73 features).
4. **Phase 4C Final Report:**  
   `outputs/phase_4c_ml/PHASE_4C_ML_PREPARATION_REPORT.md`.
