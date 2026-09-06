# Phase 2C - Step 3: Spatial Context and Distance Reprocessing Report

**Date:** 2026-09-02  
**Phase:** 2C Step 3 - Spatial Context and Distance Reprocessing  
**Test result:** 12/12 passed  
**Status:** COMPLETE - STOP after this step. No model retraining.

---

## 1. CRS / Distance Methodology

### 1.1 Previous Approach - EPSG:32643 (UTM Zone 43N)

The project previously used **EPSG:32643 (UTM Zone 43N)** for projected-distance
calculations. This CRS has a central meridian of **75.0 E** and is formally valid
from 72 E to 78 E.

Tamil Nadu spans **76.23 E to 80.35 E**, which means:

| Region | Longitude | Offset from UTM 43N centre | Distortion |
|---|---|---|---|
| Western TN (Kerala border) | 76.23 E | 1.23 deg | Negligible |
| UTM 43N/44N boundary | 78.00 E | 3.00 deg | Small |
| Eastern TN (coast/Chennai) | 80.35 E | 5.35 deg | Non-trivial |

Tamil Nadu **straddles the UTM 43N / 44N boundary at 78 E**. Using a single UTM 43N
projection introduces increasing scale distortion eastward.

### 1.2 Quantified Distortion

Concrete test: two points 1 km apart near Chennai (80.3 E):

| Method | Distance | Error |
|---|---|---|
| Haversine (WGS84 geodesic) | 1,000.75 m | (reference) |
| UTM 43N projected distance | 999.36 m | **1.40 m absolute / 0.140%** |

At 5 km true distance, UTM 43N error = **7 m**. Small in absolute terms, but
distortion grows non-linearly toward the eastern boundary.

### 1.3 Adopted Method - WGS84 Haversine (sklearn BallTree)

**Phase 2C adopts WGS84 geodesic distance (Haversine metric) via
`sklearn.neighbors.BallTree(metric='haversine')`.**

Rationale:
1. **Correct across both UTM zones.** No projection boundary artifacts.
2. **Zero computational overhead** - BallTree with haversine is as efficient as any projected approach.
3. **No dependency on pyproj/GDAL projection** for core distance logic.
4. **Exact** for spherical Earth - sufficient for industrial proximity features at metre-to-km scales.

The change from UTM 43N to Haversine produces at most ~7 m difference at 5 km range.
**This does not materially affect any feature, threshold, or classification decision.**

> NOTE: The change is scoped to spatial_features.py only. No other CRS references
> elsewhere in the project have been modified.

---

## 2. OSM Coverage Status - Failed-Tile Tracking

Phase 2C OSM retrieval produced 11,429 facilities from **9/16 tiles**
(7 tiles failed due to Overpass API timeouts).

### 2.1 Event Coverage Distribution

| Coverage Status | Count | % | Interpretation |
|---|---:|---:|---|
| **COVERED** | 325 | 51.3% | Inside a successful tile - OSM data available |
| **FAILED_TILE** | 308 | 48.7% | Inside a failed tile - OSM data unavailable, NOT absent |
| **OUTSIDE** | 0 | 0.0% | Outside all tile boundaries |

> **IMPORTANT:** 308 events (48.7%) fall within failed OSM tiles. Their distances
> are measured to the nearest facility from a *different, successful tile* - up to
> 90+ km away. These distances are NOT evidence of genuine remoteness from industry.

### 2.2 Failed Tiles Affecting FIRMS Events

| Tile ID | Bounds | Events | Known Industrial Significance |
|---|---|---:|---|
| tile_4_4 | [12.16, 79.31, 13.54, 80.35] | **195** | Chennai/Ennore coast - North Chennai power plants, Ennore LNG, petrochemical corridor |
| tile_1_2 | [8.08, 77.25, 9.46, 78.30] | 38 | Tuticorin - SPIC, Sterlite, Tuticorin Thermal Power Station |
| tile_3_1 | [10.80, 76.23, 12.18, 77.27] | 33 | Western Coimbatore - textile mills, engineering industry |
| tile_4_2 | [12.16, 77.25, 13.54, 78.30] | 33 | Vellore-Tiruvannamalai - tanning, light manufacturing |
| tile_4_3 | [12.16, 78.28, 13.54, 79.33] | 5 | Kanchipuram - brick kilns, light industry |
| tile_2_1 | [9.44, 76.23, 10.82, 77.27] | 3 | Palakkad gap / western fringe |
| tile_2_4 | [9.44, 79.31, 10.82, 80.35] | 1 | East coast fringe |

> **CAUTION:** 195 of the 308 FAILED_TILE events (63%) are in tile_4_4 (Chennai/Ennore coast).
> This is one of Tamil Nadu's most industrially dense regions. Treating these events as
> "remote from industrial facilities" would be methodologically incorrect.

---

## 3. Spatial Proximity Results

### 3.1 Nearest ANY Facility - Summary Statistics (all 633 events, Haversine)

| Statistic | Distance |
|---|---|
| Minimum | 25 m |
| P10 | 355 m |
| P25 | 1,336 m (1.3 km) |
| **Median** | **9,483 m (9.5 km)** |
| Mean | 40,717 m (40.7 km) |
| P75 | 88,663 m (88.7 km) |
| P90 | 116,662 m (116.7 km) |
| P95 | 137,308 m (137.3 km) |
| Maximum | 143,651 m (143.7 km) |

> NOTE: The high median (9.5 km) and mean (40.7 km) are dominated by the 308
> FAILED_TILE events. See Section 3.3 for the COVERED-only breakdown.

### 3.2 Distance Bands - ANY Facility (all 633 events)

| Threshold | Count | % |
|---|---:|---:|
| <= 500 m | 121 | 19.1% |
| <= 1 km | 151 | 23.9% |
| <= 2 km | 189 | 29.9% |
| <= 5 km | 284 | 44.9% |
| <= 10 km | 318 | 50.2% |

### 3.3 Distance by OSM Coverage Status - CRITICAL SPLIT

| Metric | COVERED (n=325) | FAILED_TILE (n=308) |
|---|---|---|
| Median distance to any facility | **1,412 m (1.4 km)** | 91,483 m (91.5 km) - ARTIFACT |
| Events <= 2 km | **189 / 325 (58.2%)** | 0 / 308 (0.0%) - ARTIFACT |
| Events <= 5 km | **284 / 325 (87.4%)** | 0 / 308 (0.0%) - ARTIFACT |

All 189 events within 2 km are COVERED events. The zero count for FAILED_TILE
events is a retrieval gap artifact, not a spatial reality.

### 3.4 Nearest ANY Facility - Threshold Sensitivity (all 633 events)

| Threshold | Events | % | Marginal gain |
|---|---:|---:|---:|
| 0.5 km | 121 | 19.1% | +121 |
| 1.0 km | 151 | 23.9% | +30 |
| 1.5 km | 169 | 26.7% | +18 |
| 2.0 km | 189 | 29.9% | +20 |
| 3.0 km | 232 | 36.7% | +43 |
| 5.0 km | 284 | 44.9% | +52 |
| 7.5 km | 310 | 49.0% | +26 |
| 10.0 km | 318 | 50.2% | +8 |

### 3.5 Nearest HIGHER_RELEVANCE Facility - Summary Statistics

(HIGHER_RELEVANCE = refineries, power plants, steel, cement, mining, oil/gas, manufacturing works)

| Statistic | Distance |
|---|---|
| Minimum | 49 m |
| P10 | 480 m |
| P25 | 2,179 m (2.2 km) |
| **Median** | **14,844 m (14.8 km)** |
| Mean | 43,034 m (43.0 km) |
| P75 | 88,663 m (88.7 km) |
| P90 | 122,338 m (122.3 km) |
| Maximum | 145,010 m (145.0 km) |

### 3.6 Distance Bands - HIGHER_RELEVANCE Only (all 633 events)

| Threshold | Count | % |
|---|---:|---:|
| <= 500 m | 66 | 10.4% |
| <= 1 km | 139 | 22.0% |
| <= 2 km | 154 | 24.3% |
| <= 5 km | 217 | 34.3% |
| <= 10 km | 276 | 43.6% |

### 3.7 HIGHER_RELEVANCE - Threshold Sensitivity

| Threshold | Events | % | Marginal gain |
|---|---:|---:|---:|
| 0.5 km | 66 | 10.4% | +66 |
| 1.0 km | 139 | 22.0% | +73 |
| 1.5 km | 146 | 23.1% | +7 |
| 2.0 km | 154 | 24.3% | +8 |
| 3.0 km | 183 | 28.9% | +29 |
| 5.0 km | 217 | 34.3% | +34 |
| 7.5 km | 257 | 40.6% | +40 |
| 10.0 km | 276 | 43.6% | +19 |

---

## 4. OSM Category and Relevance Distribution

### 4.1 Nearest Facility Category (events <= 5 km only, n=284)

| Category | Count | % | Relevance Tier |
|---|---:|---:|---|
| Substation & Electrical Infrastructure | 138 | 48.6% | CAUTION_LOWER_RELEVANCE |
| Industrial Area / Zone | 40 | 14.1% | GENERAL_CONTEXT |
| Steel / Metallurgy | 31 | 10.9% | HIGHER_RELEVANCE |
| Mining & Quarry | 30 | 10.6% | HIGHER_RELEVANCE |
| Power Plant | 29 | 10.2% | HIGHER_RELEVANCE |
| Manufacturing & Industrial Works | 9 | 3.2% | HIGHER_RELEVANCE |
| Oil, Gas & Chemical | 3 | 1.1% | HIGHER_RELEVANCE |
| Generic Industrial Building | 2 | 0.7% | GENERAL_CONTEXT |
| Cement & Construction Materials | 2 | 0.7% | HIGHER_RELEVANCE |

> NOTE: 48.6% of events within 5 km have a substation as their nearest OSM match.
> Substations are CAUTION_LOWER_RELEVANCE. This does NOT indicate an industrial fire
> source. The relevance_tier column in the enriched dataset explicitly distinguishes
> this from a HIGHER_RELEVANCE match.

### 4.2 Nearest Facility Relevance Tier (all 633 events)

| Tier | Count | % |
|---|---:|---:|
| HIGHER_RELEVANCE | 250 | 39.5% |
| CAUTION_LOWER_RELEVANCE | 201 | 31.8% |
| GENERAL_CONTEXT | 182 | 28.8% |

---

## 5. 2 km Threshold Evaluation

### 5.1 Evidence Summary

| Statistic | Value |
|---|---|
| Events within 2 km (any facility, all 633) | 189 / 633 = 29.9% |
| Events within 2 km (HIGHER_RELEVANCE, all 633) | 154 / 633 = 24.3% |
| Events within 2 km among COVERED events only | 189 / 325 = **58.2%** |
| Events within 2 km among FAILED_TILE events | 0 / 308 = 0.0% (artifact) |
| Marginal gain 1.5 km to 2.0 km (any) | +20 events |
| Marginal gain 2.0 km to 3.0 km (any) | +43 events |
| Marginal gain 1.5 km to 2.0 km (HIGHER_RELEVANCE) | +8 events |
| Marginal gain 2.0 km to 3.0 km (HIGHER_RELEVANCE) | +29 events |

### 5.2 Recommendation - RETAIN 2 km with documented caveats

**Retain 2 km as the baseline industrial-context proximity threshold.**

Why 2 km is defensible:
1. Among COVERED events (valid OSM data), **58.2% fall within 2 km** of an OSM
   industrial object, indicating genuine spatial co-location.
2. The marginal gain from 1.5 to 2.0 km (+20 events, any) rises sharply to
   3.0 km (+43 events), suggesting 2 km captures the dense inner cluster.
3. 2 km is consistent with the scale of industrial complexes and VIIRS pixel
   resolution (~375 m).
4. At 2 km (HIGHER_RELEVANCE), 24.3% of all events - 47.4% of COVERED events -
   are within range of a facility with direct thermal emission potential.

Why a threshold change is NOT recommended at this time:
- 48.7% of events have unreliable OSM distances (FAILED_TILE artifacts).
- A threshold decision based on the full 633-event distribution is distorted.
- Correct action: retry the 7 failed tiles, then re-evaluate.

> **WARNING:** The 2 km threshold must NOT be applied to FAILED_TILE events as
> a positive proximity signal. The osm_coverage_status column explicitly flags
> this for downstream human validation.

**The project 2 km threshold is NOT silently changed. It is retained with
these documented limitations.**

---

## 6. Output File

### 6.1 firms_spatially_enriched_v2.csv

- **Path:** `outputs/ground_truth_investigation/firms_spatially_enriched_v2.csv`
- **Rows:** 633 (original population preserved)
- **Columns:** 43

Column groups:

| Group | Columns |
|---|---|
| Original FIRMS fields | latitude, longitude, brightness, frp, confidence, acq_date, acq_time, ... |
| WorldCover (Step 1) | landcover_code, landcover_class |
| OSM Coverage | osm_coverage_status (COVERED / FAILED_TILE / OUTSIDE) |
| Any facility proximity | distance_to_facility_m/km, nearest_facility_osm_id/type/name/type/category/tier |
| Any facility distance bands | near_industrial_500m through near_industrial_10000m |
| HIGHER_RELEVANCE proximity | distance_to_higher_relevance_m/km, nearest_hr_osm_id/name/category |
| HIGHER_RELEVANCE distance bands | near_higher_relevance_500m through near_higher_relevance_10000m |
| General context | distance_to_general_context_m |

---

## 7. Test Results

All 12 project unit tests pass:

```
tests/test_feature_engineering.py::test_confidence_encoding                    PASSED
tests/test_feature_engineering.py::test_thermal_features_calculation           PASSED
tests/test_feature_engineering.py::test_temporal_grid_active_days_multiyear    PASSED
tests/test_feature_engineering.py::test_configurable_min_grid_obs              PASSED
tests/test_feature_engineering.py::test_spatial_features_planar_distance       PASSED  (updated for Phase 2C schema)
tests/test_firms_loader.py::test_chunked_firms_ingestion_and_bbox_filtering    PASSED
tests/test_firms_loader.py::test_polygon_filtering                             PASSED
tests/test_geo_utils.py::test_worldcover_tile_name                             PASSED
tests/test_geo_utils.py::test_reproject_gdf                                    PASSED
tests/test_geo_utils.py::test_filter_points_by_boundary                        PASSED
tests/test_weak_labeler.py::test_weak_label_landcover_aware                    PASSED
tests/test_weak_labeler.py::test_weak_label_fallback                           PASSED

12 passed in 3.66s
```

The test `test_spatial_features_planar_distance` was updated to match the Phase 2C
OSM DataFrame schema (added normalized_category and relevance_tier to the mock
fixture) and to validate the new HIGHER_RELEVANCE distance output columns.

---

## 8. Code Changes in This Step

| File | Change |
|---|---|
| `src/feature_engineering/spatial_features.py` | Already rewritten in Phase 2C (Haversine BallTree, dual ANY/HIGHER_RELEVANCE lookup) |
| `tests/test_feature_engineering.py` | Updated test_spatial_features_planar_distance for Phase 2C schema |
| `outputs/ground_truth_investigation/firms_spatially_enriched_v2.csv` | Created - 633 events with full spatial context |

---

## 9. Limitations

1. **48.7% of events are in failed OSM tiles.** All spatial proximity values for
   these 308 events are unreliable. The osm_coverage_status column flags them.

2. **Substations dominate nearest-facility results within 5 km.** 48.6% of events
   within 5 km have a substation as their nearest OSM match. Substations are
   explicitly classified as CAUTION_LOWER_RELEVANCE.

3. **OSM data quality is heterogeneous.** Named facilities are only 24.9% of the
   11,429 OSM objects. Many are small, anonymously mapped generators or industrial
   buildings with no semantic detail.

4. **Haversine uses spherical Earth.** Maximum error vs. true geodesic (ellipsoidal)
   distance is ~0.3% globally - negligible for this use case.

5. **The 2 km threshold evaluation is constrained.** A robust threshold decision
   requires complete OSM coverage across all 16 tiles.

---

## 10. Next Steps (STOP - do not proceed beyond this point)

> **CAUTION:** Step 3 is complete. Do NOT retrain the Random Forest. Do NOT create
> ground-truth labels. Do NOT proceed to candidate selection.

When authorised, recommended next actions:
1. **Retry 7 failed OSM tiles** (preferably early morning UTC, timeout=120+ seconds).
2. **Re-evaluate the 2 km threshold** after full OSM coverage is restored.
3. Proceed to human validation of the candidate batch from `validation_batch_v1.csv`.
