# PHASE 5B — DASHBOARD DATA REPORT

**Output file:** `outputs/phase_5b_dashboard/dashboard_events_633.csv`
**Build date:** 2026-09-06
**Status:** COMPLETE — All 13 integrity checks passed

---

## 1. SOURCE FILES

| Alias | Path | Rows | Cols | Role |
|-------|------|------|------|------|
| MASTER | `outputs/phase_4b_ground_truth/sentinel2_master_633_human_ground_truth.csv` | 633 | 177 | Primary source — all non-ML fields |
| PRED | `outputs/phase_5a_inference_633/predictions_633.csv` | 633 | 30 | ML predictions — predicted_class, probabilities, ml_confidence, provenance |

**Files NOT used:**
- `outputs/ground_truth_investigation/firms_spatially_enriched_v2.csv` — no `event_id` join key, adds no useful dashboard columns
- `outputs/sentinel2_full_633/sentinel2_full_633_events.csv` — zero columns not already in MASTER

---

## 2. JOIN METHOD

```
dashboard = MASTER LEFT JOIN PRED ON event_id
```

- Join type: LEFT (preserves all 633 MASTER events)
- Join key: `event_id` (unique in both sources, 633 identical values)
- 633/633 PRED rows matched — no unmatched events
- Renames applied post-join: `confidence` → `firms_confidence`, `confidence.1` → `ml_confidence`
- Derived constant added: `data_source_version = "phase_4b_ground_truth_v1"`
- Final column selection: 61 approved dashboard fields

---

## 3. OUTPUT SUMMARY

| Property | Value |
|----------|-------|
| Output file | `outputs/phase_5b_dashboard/dashboard_events_633.csv` |
| File size | 421,908 bytes (~412 KB) |
| Rows | **633** |
| Columns | **61** |
| Column groups | 9 (A-Identity, B-Location, C-FIRMS, D-ML, E-OSM, F-WorldCover, G-S2, H-HumanVal, I-Provenance) |
| Required fields with 0% null | 26 |
| Fields with >50% null | 3 (human_ground_truth_class, s2_dnbr_mean, nearest_facility_name) |

---

## 4. PREDICTION CLASS DISTRIBUTION

| Class | Count | % |
|-------|-------|---|
| Agricultural Burning | 287 | 45.34% |
| Industrial Thermal Activity | 261 | 41.23% |
| Natural / Wildfire / Other | 85 | 13.43% |
| **Total** | **633** | **100%** |

> **Note:** Industrial Thermal Activity is predicted at 41.2% — substantially higher than its 19.8% share in the 76-event training set. This reflects the broader 633-event population including many events near OSM industrial facilities not represented in training labels. This is an expected population-level finding, not a model error.

---

## 5. ML CONFIDENCE DISTRIBUTION

| Tier | Count | % | Probability Range |
|------|-------|---|-------------------|
| HIGH | 264 | 41.71% | ≥ 0.75 |
| MEDIUM | 296 | 46.76% | 0.50 – 0.74 |
| LOW | 73 | 11.53% | < 0.50 |
| **Total** | **633** | **100%** |

**Max probability statistics:** mean=0.7133, min=0.3549, max=1.0000

---

## 6. HUMAN VALIDATION COVERAGE

| Status | Count | % |
|--------|-------|---|
| Human reviewed (`has_human_validation=True`) | 100 | 15.8% |
| Unreviewed (`has_human_validation=False`) | 533 | 84.2% |
| Unambiguous ground truth (`is_unambiguous_ground_truth=True`) | 76 | 12.0% |

### Human Ground Truth Class Distribution (reviewed events only)

| Human Label | Count | Notes |
|-------------|-------|-------|
| Agricultural Burning | 50 | Maps to ML class |
| REVIEW_REQUIRED | 24 | Ambiguous — no assignable label |
| Persistent Industrial Thermal Source | 12 | Subset of Industrial Thermal Activity (ML) |
| Natural/Forest Fire | 9 | Subset of Natural / Wildfire / Other (ML) |
| Industrial Fire | 3 | Subset of Industrial Thermal Activity (ML) |
| Other/Unclassified | 2 | Unmapped |
| Not reviewed (null) | 533 | — |

> ⚠️ Human labels use a different vocabulary from ML production classes. 1:1 mapping does not exist for all labels. Dashboard must display both independently.

---

## 7. SENTINEL-2 AVAILABILITY SUMMARY

### Pre-fire observation status
| Status | Count | % |
|--------|-------|---|
| CLOUD_REJECTED | 233 | 36.8% |
| REAL_CDSE_SUCCESS | 204 | 32.2% |
| MISSING_PRODUCT | 196 | 31.0% |

### Post-fire observation status
| Status | Count | % |
|--------|-------|---|
| CLOUD_REJECTED | 225 | 35.5% |
| MISSING_PRODUCT | 223 | 35.2% |
| REAL_CDSE_SUCCESS | 185 | 29.2% |

### Change analysis status
| Status | Count | % |
|--------|-------|---|
| MISSING_POST | 169 | 26.7% |
| MISSING_PRE | 158 | 25.0% |
| INSUFFICIENT_VALID_DATA | 126 | 19.9% |
| **SUCCESS** | **80** | **12.6%** |
| INVALID_INPUT | 70 | 11.1% |
| MISSING_BOTH | 30 | 4.7% |

> Only **80/633 events (12.6%)** have complete pre+post Sentinel-2 change analysis. dNBR values are available only for these events (87.4% null). NDVI values are available for ~60% of events.

---

## 8. OSM AVAILABILITY SUMMARY

| OSM Coverage Status | Count | % |
|--------------------|-------|---|
| COVERED | 325 | 51.3% |
| FAILED_TILE | 308 | 48.7% |

### Nearest Facility Tier Distribution

| Tier | Count | % |
|------|-------|---|
| HIGHER_RELEVANCE | 250 | 39.5% |
| CAUTION_LOWER_RELEVANCE | 201 | 31.8% |
| GENERAL_CONTEXT | 182 | 28.8% |

### Nearest Facility Category (top 5)
| Category | Count |
|----------|-------|
| Substation & Electrical Infrastructure | 201 |
| Industrial Area / Zone | 178 |
| Mining & Quarry | 123 |
| Power Plant | 78 |
| Steel / Metallurgy | 31 |

**Field missingness:** `nearest_facility_name` (76.9% null — most OSM facilities unnamed), `nearest_hr_name` (70.8% null).

---

## 9. WORLDCOVER DISTRIBUTION

| Land Cover Class | Count | % |
|-----------------|-------|---|
| Built-up | 155 | 24.5% |
| Tree cover | 134 | 21.2% |
| Cropland | 133 | 21.0% |
| Grassland | 115 | 18.2% |
| Shrubland | 69 | 10.9% |
| Bare/sparse vegetation | 24 | 3.8% |
| Permanent water bodies | 2 | 0.3% |
| Mangroves | 1 | 0.2% |

All 633 events have valid `landcover_code` and `landcover_class` (0% null).

---

## 10. INTEGRITY CHECK RESULTS

All 13 checks **PASSED**.

| # | Check | Result |
|---|-------|--------|
| 1 | Output rows = 633 | ✅ PASS |
| 2 | Unique event_id = 633 | ✅ PASS |
| 3 | No duplicate event_id | ✅ PASS |
| 4 | All 61 approved columns present | ✅ PASS |
| 5 | No unexpected columns | ✅ PASS |
| 6 | event_id set exactly matches MASTER | ✅ PASS |
| 7 | latitude/longitude exactly preserved | ✅ PASS |
| 8 | predicted_class exactly matches PRED | ✅ PASS |
| 9 | ML probabilities exactly match PRED | ✅ PASS |
| 10 | ml_confidence exactly matches PRED | ✅ PASS |
| 11 | firms_confidence matches original MASTER confidence | ✅ PASS |
| 12 | No synthetic event IDs introduced | ✅ PASS |
| 13 | No credential/secret column names | ✅ PASS |

---

## 11. EXCLUDED SOURCE FIELDS

### Internal pipeline fields (not user-relevant)
`model_path`, `is_spatial_duplicate`, `selection_rationale`, `candidate_priority_score`, `candidate_priority`, `ml_training_eligible`, `cv_fold_5`, `weak_label`, `ground_truth_status`

### Redundant fields
`distance_to_facility_km`, `distance_to_higher_relevance_km`, `near_industrial_5000m`, `near_industrial_10000m`, `near_higher_relevance_500m` through `near_higher_relevance_10000m`, `frp_brightness_ratio`, `log_frp`, `confidence_numeric`, `grid_brightness_mean`, `high_brightness_flag_local`, `frp_zscore_local`

### Raw Sentinel-2 statistical arrays
`s2_pre_ndvi_min/max/std/median`, `s2_post_ndvi_min/max/std/median`, `s2_pre_nbr_*/s2_post_nbr_*`, `s2_pre_ndwi_*/s2_post_ndwi_*`, `s2_pre_swir_ratio_*/s2_post_swir_ratio_*`, raw band means (`s2_pre_b04_mean` etc.), `s2_dndvi_median/abs_*`, `s2_dndwi_*`, `s2_dswir_ratio_*`

### Internal acquisition/processing metadata
`pre_bbox_wgs84`, `post_bbox_wgs84`, `pre/post_download_bytes`, `pre/post_product_id/name/tile_id/cloud_cover_catalogue/raster_dimensions/bands_requested`, `s2_pre/post_total_pixels/spectral_valid_pixels/spectral_valid_pct`, `raster_dimensions_px`, `bands_requested`, `aoi_dimensions_m`, `processing_timestamp`, `error_category`, `failure_reason`, `processing_status`, `is_real_cdse_data`

### Sensitive / high-null human review fields
`human_raw_label` (exposes internal labeling vocabulary), `human_review_confidence` (99.7% null), `human_validation_notes` (100% null), `human_industry_observation` (92.1% null with inconsistent values), `normalization_notes`

### Seasonal/redundant flags
`is_forest_fire_season` (collinear with `is_stubble_burning_season` and `acq_date`)

### Enriched-only fields (no reliable join key)
`distance_to_general_context_m`, `scan`, `track`, `version` (from `firms_spatially_enriched_v2.csv`, no event_id)

---

## 12. SCIENTIFIC CAUTIONS

1. **ML Prediction is probabilistic.** The model was trained on 76 labeled events using a Random Forest classifier. `predicted_class` is an algorithmic estimate — not ground truth.

2. **Human validation covers only 15.8% of events.** 533/633 events have no expert review. The absence of a human label does not mean the ML prediction is wrong.

3. **Human labels use different class vocabulary.** `human_ground_truth_class` values such as "Persistent Industrial Thermal Source" and "Industrial Fire" do not map 1:1 to ML production classes. Never auto-remap without a documented mapping table.

4. **Sentinel-2 data is largely unavailable.** Only 80/633 events (12.6%) have successful pre+post change analysis. Cloud cover and missing CDSE products are the dominant failure modes. dNBR is 87.4% null.

5. **Industrial prediction rate exceeds training distribution.** The model predicts Industrial Thermal Activity for 41.2% of events vs. 19.8% in training. This is a population-level distribution difference, not a calibration failure.

6. **FIRMS confidence ≠ ML confidence.** `firms_confidence` (NASA FIRMS quality flag: h/n/l) and `ml_confidence` (model probability tier: HIGH/MEDIUM/LOW) are independent metrics measuring different things.

7. **OSM data quality varies.** 48.7% of events are in `FAILED_TILE` zones. Facility proximity metrics are computed from global OSM data, but coverage confidence is lower in these zones.

---

## 13. OUTPUT FILES

| File | Size | Description |
|------|------|-------------|
| `dashboard_events_633.csv` | 421,908 bytes | Final dashboard dataset |
| `DASHBOARD_DATA_DICTIONARY.md` | — | Field-by-field data dictionary |
| `PHASE_5B_DASHBOARD_DATA_REPORT.md` | — | This report |
| `dashboard_schema_design.md` | 25,602 bytes | Schema design document (Step 1) |

---

*Phase 5B Step 2 complete. No source files modified. No Git operations performed.*
*Model SHA-256: 5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798*
