# Phase 2C Final Synthesis: Data Correction, Spatial Enrichment, and Validation Batch Curation Report

**Date:** 2026-09-02  
**Status:** PHASE 2C COMPLETE — All Steps (1–5) Concluded  
**Scope:** Data Correction, Spatial Processing, Candidate Curation, and Validation Protocol Specification  

---

## Executive Summary

Phase 2C resolved the critical spatial and cache defects discovered during Phase 2B audits and established an uncorrupted, diverse candidate dataset and validation protocol for human ground-truth evaluation. 

Across Phase 2C:
1. **Step 1 (WorldCover Cache Correction):** Completely eliminated the stale 76.94% Unknown rate in ESA WorldCover data, achieving **100.0% valid coverage (0.0% Unknown)** across all 633 Tamil Nadu FIRMS events.
2. **Step 2 (OSM Retrieval Expansion):** Expanded geographic OSM retrieval across 16 tiles in Tamil Nadu, extracting **11,429 deduplicated industrial objects** categorized into a 3-tier semantic relevance hierarchy.
3. **Step 3 (Spatial Context & Metric Reprocessing):** Replaced distorted degree-space Euclidean distance with rigorous geodesic Haversine distance, explicitly tracking `osm_coverage_status` (51.3% COVERED, 48.7% FAILED_TILE) and revealing that generic electrical substations accounted for ~48.6% of nearby OSM objects.
4. **Step 4 (Diverse Validation Batch Curation):** Developed an objective 10-stratum sampling algorithm with spatial deduplication (195 duplicates flagged) to curate a **100-event diverse validation batch** (`validation_batch_v1.csv`) covering all 8 land-cover classes, geographic extremes, and critical coverage gaps (e.g., Chennai/Ennore and Tuticorin).
5. **Step 5 (Human Validation Protocol):** Established `VALIDATION_PROTOCOL_V1.md` providing a 6-class ontology, 3 confidence tiers, evidence hierarchies, and strict ground-truth rules for human reviewers.

**Key Rule Maintained:** Candidate selection is **NOT** ground truth. All 633 candidates in `validation_candidates_v2.csv` and all 100 events in `validation_batch_v1.csv` remain strictly marked `ground_truth_status = UNVERIFIED`. No model retraining or automated label assignment occurred.

---

## 1. Step 1: WorldCover Cache Correction

### 1.1 Problem & Root Cause
In Phase 2B, 487 out of 633 FIRMS events (76.94%) were assigned `Unknown` land cover because the local sampler looked for pre-downloaded GeoTIFFs matching an unpadded naming format and defaulted to `Unknown` rather than downloading or querying the active ESA WorldCover v200 AWS S3/Zenodo endpoints.

### 1.2 Resolution & Verification
- Cleaned stale cache structures and integrated direct tile sampling.
- Re-sampled all 633 FIRMS events across Tamil Nadu.
- Valid samples: **633 / 633 (100.00%)**.
- Unknown samples: **0 / 633 (0.00%)**.

### 1.3 WorldCover Class Distribution (n=633)
| WorldCover Class | Count | Percentage |
|---|---:|---:|
| Built-up | 155 | 24.49% |
| Tree cover | 134 | 21.17% |
| Cropland | 133 | 21.01% |
| Grassland | 115 | 18.17% |
| Shrubland | 69 | 10.90% |
| Bare / sparse vegetation | 24 | 3.79% |
| Permanent water bodies | 2 | 0.32% |
| Mangroves | 1 | 0.16% |
| **Total** | **633** | **100.00%** |

---

## 2. Step 2: OSM Retrieval Expansion & Semantic Hierarchy

### 2.1 Tiled Overpass Retrieval
Tamil Nadu bounding box (8.08°S–13.54°N, 76.23°W–80.35°E) was partitioned into a 4×4 grid (16 tiles). Queries targeted industrial infrastructure (`landuse=industrial`, `man_made=*`, `power=*`, `building=industrial`).

- **Successful Tiles:** 9 / 16 (56.25%)
- **Failed Tiles (Overpass Timeouts):** 7 / 16 (43.75%), notably dense coastal/industrial corridors:
  - `tile_4_4` (Chennai / Manali / Ennore)
  - `tile_1_2` (Tuticorin port / industrial belt)
  - `tile_3_1` (Western Coimbatore / Nilgiris)
  - `tile_3_3`, `tile_4_3`, `tile_1_3`, `tile_4_1`
- **Total Deduplicated Objects Retrieved:** **11,429**

### 2.2 Semantic Category Breakdown
| Category | Count | Share (%) | Assigned Tier |
|---|---:|---:|---|
| Power Substation / Infrastructure | 5,558 | 48.63% | `CAUTION_LOWER_RELEVANCE` |
| Industrial Zone / Landuse | 2,912 | 25.48% | `GENERAL_CONTEXT` |
| Factory / Industrial Works | 1,061 | 9.28% | `HIGHER_RELEVANCE` |
| Power Plant / Generator | 888 | 7.77% | `HIGHER_RELEVANCE` |
| Mining / Quarry | 580 | 5.07% | `HIGHER_RELEVANCE` |
| Generic Industrial Building | 378 | 3.31% | `CAUTION_LOWER_RELEVANCE` |
| Refinery / Petrochemical | 35 | 0.31% | `HIGHER_RELEVANCE` |
| LNG / Oil / Gas Storage | 17 | 0.15% | `HIGHER_RELEVANCE` |
| **Total** | **11,429** | **100.00%** | |

### 2.3 Semantic Relevance Tier Totals
| Relevance Tier | Count | Share (%) | Description |
|---|---:|---:|---|
| `CAUTION_LOWER_RELEVANCE` | 5,936 | 51.94% | Substations and generic buildings (non-thermal emitters) |
| `GENERAL_CONTEXT` | 2,912 | 25.48% | Polygons of industrial estates and land parcels |
| `HIGHER_RELEVANCE` | 2,581 | 22.58% | Heavy thermal/industrial facilities (refineries, power plants, kilns) |

---

## 3. Step 3: Spatial Context, CRS Correction, and Proximity Analysis

### 3.1 Metric Distance Calculation
Replaced non-metric degree Euclidean calculation ($\sqrt{\Delta \text{lat}^2 + \Delta \text{lon}^2}$) with geodesic Haversine distance in meters.

### 3.2 OSM Coverage Status across Population (n=633)
| Status | Event Count | Share (%) | Meaning |
|---|---:|---:|---|
| `COVERED` | 325 | 51.34% | Event fell inside one of the 9 successful OSM tiles |
| `FAILED_TILE` | 308 | 48.66% | Event fell inside one of 7 failed Overpass tiles (OSM unknown) |

**Breakdown of FAILED_TILE Events:**
- Chennai / Manali / Ennore (`tile_4_4`): 195 events (30.8% of total population)
- Tuticorin (`tile_1_2`): 38 events (6.0% of total population)
- Other failed tiles: 75 events (11.8% of total population)

### 3.3 Proximity Distribution to Any OSM Facility
| Distance Threshold | Events Count | Share (%) |
|---|---:|---:|
| $\le$ 500 m | 121 | 19.12% |
| $\le$ 1.0 km | 151 | 23.85% |
| $\le$ 2.0 km (Baseline Context) | 189 | 29.86% |
| $\le$ 5.0 km | 284 | 44.87% |
| $\le$ 10.0 km | 318 | 50.24% |
| > 10.0 km | 315 | 49.76% |

### 3.4 Proximity Distribution to HIGHER_RELEVANCE Facilities
| Distance Threshold | Events Count | Share (%) |
|---|---:|---:|
| $\le$ 500 m | 15 | 2.37% |
| $\le$ 1.0 km | 26 | 4.11% |
| $\le$ 2.0 km | 48 | 7.58% |
| $\le$ 5.0 km | 98 | 15.48% |
| $\le$ 10.0 km | 161 | 25.43% |
| > 10.0 km | 472 | 74.57% |

### 3.5 Key Findings & 2 km Threshold Assessment
1. **Substation Bias:** 48.6% of objects within 5 km were electrical substations (`power=substation`). Substations do not produce open combustion thermal plumes, proving that distance to generic OSM infrastructure cannot be used as an automatic labeler.
2. **2 km Baseline Rule Invalidated as Ground Truth:** While 2 km remains a standard spatial feature token, proximity alone is purely contextual.

---

## 4. Step 4: Candidate Selection & Diverse Validation Batch

### 4.1 Merging & Scoring
Merged Step 3 spatial attributes with the 31-feature baseline table (`TamilNadu_Classified_Fires.csv`).
Computed a 5-component `candidate_priority_score` (0.0 to 1.0) weighting:
- Industrial context (30%)
- Thermal intensity / FRP (25%)
- Grid persistence (20%)
- Coverage-gap bonus for Chennai/Tuticorin (15%)
- FIRMS detection confidence (10%)

### 4.2 Spatial Deduplication
- Grouped events within **5.5 km** on the **same acquisition date**.
- Flagged **195 events (30.8%)** as `is_spatial_duplicate = True` to prevent cluster over-representation while leaving all 633 records intact.
- Non-duplicate pool: **438 events**.

### 4.3 10-Stratum Sampling Breakdown (n=100)
| Stratum ID | Stratum Definition | Selected Count |
|---|---|---:|
| S1 | COVERED + HIGHER_RELEVANCE + $\le$ 500 m | 12 |
| S2 | COVERED + HIGHER_RELEVANCE + 500 m to 2 km | 12 |
| S3 | COVERED + HIGHER_RELEVANCE + 2 km to 5 km | 8 |
| S4 | COVERED + CAUTION / GENERAL tier | 10 |
| S5 | COVERED + Far from industry (> 5 km) | 8 |
| S6 | FAILED_TILE — Chennai / Ennore Corridor | 20 |
| S7 | FAILED_TILE — Tuticorin Industrial Hub | 10 |
| S8 | FAILED_TILE — Other Regions | 10 |
| S9 | Thermal Intensity Outliers (FRP $\ge$ 5 MW) | 5 |
| S10 | Persistent Locations (Grid Active Days $\ge$ 10) | 5 |
| **Total** | | **100** |

### 4.4 Diversity Comparison: Batch (n=100) vs Population (n=633)
| Feature Dimension | Full Population (n=633) | Validation Batch (n=100) |
|---|---:|---:|
| **OSM Status: COVERED** | 51.3% | 56.0% (n=56) |
| **OSM Status: FAILED_TILE** | 48.7% | 44.0% (n=44) |
| **Nearest Tier: HIGHER_RELEVANCE** | 39.5% | 63.0% (n=63) |
| **Nearest Tier: GENERAL_CONTEXT** | 28.8% | 19.0% (n=19) |
| **Nearest Tier: CAUTION_LOWER_REL** | 31.8% | 18.0% (n=18) |
| **Land Cover: Cropland** | 21.0% | 31.0% (n=31) |
| **Land Cover: Tree cover** | 21.2% | 24.0% (n=24) |
| **Land Cover: Grassland** | 18.2% | 22.0% (n=22) |
| **Land Cover: Built-up** | 24.5% | 12.0% (n=12) |
| **Land Cover: Shrubland** | 10.9% | 6.0% (n=6) |
| **Land Cover: Bare / Sparse** | 3.8% | 3.0% (n=3) |
| **Land Cover: Water / Mangrove** | 0.5% | 2.0% (n=2) |
| **FRP $\ge$ 5 MW** | 8.8% | 32.0% (n=32) |
| **Sensor: VIIRS N20 / SUOMI_NPP** | 53.9% / 46.1% | 59.0% / 41.0% |
| **Temporal: Nov / Dec / Jan** | 22.1% / 37.6% / 40.3% | 31.0% / 37.0% / 32.0% |
| **Priority: HIGH / MED / LOW** | 12.6% / 61.6% / 25.8% | 20.0% / 72.0% / 8.0% |
| **Ground Truth Status: UNVERIFIED** | **100.0%** | **100.0%** |

---

## 5. Step 5: Validation Protocol Overview

The human validation protocol was codified in [`VALIDATION_PROTOCOL_V1.md`](./VALIDATION_PROTOCOL_V1.md).

### 5.1 Six Validation Classes
1. **Industrial Fire:** Uncontrolled, accidental emergency fire at an industrial facility.
2. **Persistent Industrial Thermal Source:** Legitimate, continuous/recurring heat emission from normal operations (boilers, kilns, flaring).
3. **Agricultural Burning:** Crop residue or field stubble combustion.
4. **Natural / Forest Fire:** Wildfire in vegetation (forest, scrubland, grassland).
5. **Other / Unclassified:** Identified non-industrial/non-agricultural events (waste burning, construction).
6. **Unknown / Insufficient Evidence:** Valid outcome when independent data is lacking or contradictory.

### 5.2 Confidence Levels & Evidence Hierarchy
- **Confidence:** High, Medium, Low (measuring strength of evidence, not model probability).
- **High-Value Evidence:** Official regulatory records, TNPCB incident logs, fire dept reports, verified high-resolution optical satellite burn scars.
- **Supporting Evidence:** Reputable news articles, OSM facility metadata, WorldCover class, FIRMS persistence/FRP.
- **Weaker Evidence:** Proximity alone, WorldCover alone, heuristic priority scores, ML predictions.

---

## 6. Project Artifacts & Files Summary

| File Path | Description | Records |
|---|---|---:|
| `outputs/ground_truth_investigation/firms_spatially_enriched_v2.csv` | Spatial & WorldCover enriched dataset | 633 rows |
| `outputs/ground_truth_investigation/validation_candidates_v2.csv` | Full candidate pool with priority & deduplication flags | 633 rows |
| `outputs/ground_truth_investigation/validation_batch_v1.csv` | Curated diverse subset for human review | 100 rows |
| `VALIDATION_PROTOCOL_V1.md` | Standalone human validation protocol guide | — |
| `PHASE_2C_CANDIDATE_SELECTION_REPORT.md` | Detailed selection & stratum design report | — |
| `PHASE_2C_SPATIAL_REPROCESSING_REPORT.md` | Geodesic spatial analysis & OSM breakdown report | — |
| `PHASE_2C_OSM_RETRIEVAL_REPORT.md` | Tiled Overpass retrieval report | — |
| `PHASE_2C_WORLDCOVER_FIX_REPORT.md` | Step 1 WorldCover fix report | — |

---

## 7. Known Limitations & Recommendations for Future Phases

### Limitations
1. **OSM Retrieval Gaps:** 7 of 16 tiles experienced Overpass timeouts. Future work can implement bounded sub-queries with local Overpass Docker instances or Planet OSM extracts.
2. **Temporal Window:** Current data covers Nov 2024–Jan 2025. Seasonal variations across monsoon and pre-monsoon periods are not yet captured.
3. **Absence of S2 Optical Integration:** Sentinel-2 optical imagery has not yet been fetched or processed; optical burn scars remain an external manual check.

### Recommended Next Steps (Phase 3)
1. **Execute Human Validation:** Human reviewers follow `VALIDATION_PROTOCOL_V1.md` to populate labels on `validation_batch_v1.csv`.
2. **Benchmark Baseline:** Evaluate the existing 31-feature baseline model against the independently validated ground-truth sample.
3. **Incorporate Sentinel-2 & Multi-Modal Features:** Download optical/SWIR surface reflectance tiles for verified candidate locations to enrich feature representations.

---
