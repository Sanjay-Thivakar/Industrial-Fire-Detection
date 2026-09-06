# Phase 2C - Step 4: Diverse Human Validation Batch - Candidate Selection Report

**Date:** 2026-09-02
**Phase:** 2C Step 4 - Candidate Curation
**Status:** COMPLETE - STOP after this step. Human validation not yet performed.

---

## 1. Overview

| Item | Value |
|---|---|
| Source population | 633 FIRMS events (Tamil Nadu, Nov 2024 - Jan 2025) |
| Events selected for validation batch | **100** |
| Batch name | Diverse Validation Batch |
| All candidates status | **UNVERIFIED** |
| Ground-truth labels assigned | **None** |
| Model retrained | No |
| Sentinel-2 implemented | No |

This step curates a **diverse** set of FIRMS events for future human review.
It is candidate curation only. No ground-truth labels are inferred from
OSM proximity, WorldCover, FRP, persistence, or any other feature.

---

## 2. Source Data

The selection merged:

| Source | Rows | Key Contribution |
|---|---:|---|
| `firms_spatially_enriched_v2.csv` (Step 3) | 633 | OSM proximity, WorldCover, osm_coverage_status |
| `TamilNadu_Classified_Fires.csv` | 633 | Persistence features, thermal features, 31-feature set |

Both datasets share `row_id` (0-632). Merged on `row_id`. Final merged dataset: **633 rows, 68 columns**.

---

## 3. Priority Scoring Methodology

Each event receives a **candidate priority score** (0-1) reflecting its
investigative usefulness, NOT its probability of being an industrial fire.

Priority is NOT a class prediction. HIGH priority does NOT mean "industrial fire".

### 3.1 Score Components

| Component | Weight | Description |
|---|---:|---|
| Industrial context (a) | 30% | OSM proximity + relevance tier for COVERED events; base 0.4 for FAILED_TILE (coverage unavailable, not absence) |
| Thermal intensity (b) | 25% | log(FRP) + brightness difference, both normalized |
| Persistence (c) | 20% | grid_active_days / 20 (max observed) |
| Coverage gap bonus (d) | 15% | +0.15 for FAILED_TILE events in Chennai/Ennore or Tuticorin (high industrial density) |
| Detection confidence (e) | 10% | h=1.0, n=0.5, l=0.2, numeric/100 |

### 3.2 Priority Tiers (full population, n=633)

| Tier | Threshold | Count | % |
|---|---|---:|---:|
| HIGH | score >= 0.50 | 80 | 12.6% |
| MEDIUM | 0.30 <= score < 0.50 | 390 | 61.6% |
| LOW | score < 0.30 | 163 | 25.8% |

### 3.3 Priority Tiers (validation batch, n=100)

| Tier | Count | % |
|---|---:|---:|
| HIGH | 20 | 20.0% |
| MEDIUM | 72 | 72.0% |
| LOW | 8 | 8.0% |

---

## 4. Spatial Deduplication

To avoid filling the batch with near-identical detections from the same
thermal episode, events within **~5.5 km** on the **same acquisition date**
were grouped. Within each cluster, the highest-priority representative was
retained; others were flagged `is_spatial_duplicate = True`.

| Metric | Value |
|---|---|
| Events flagged as spatial duplicates | 195 (30.8%) |
| Primary (non-duplicate) events available | 438 |

**The original 633-event population is preserved intact.** Deduplication
only flags rows - it does not delete any events.

---

## 5. Selection Methodology - 10-Stratum Diversity Design

The batch was selected by greedy geographic-spread within each stratum.
Within each stratum: (1) prefer non-duplicate events, (2) start with highest
priority score, (3) iteratively add the event most geographically distant
from those already selected (equal weight: 50% spread, 50% priority score).

| Stratum | Description | Budget | Selected |
|---|---|---:|---:|
| S1 | COVERED + HIGHER_RELEVANCE + <= 500 m | 12 | 12 |
| S2 | COVERED + HIGHER_RELEVANCE + 500 m to 2 km | 12 | 12 |
| S3 | COVERED + HIGHER_RELEVANCE + 2 to 5 km | 8 | 8 |
| S4 | COVERED + CAUTION or GENERAL tier | 10 | 10 |
| S5 | COVERED + far from industrial (> 5 km) | 8 | 8 |
| S6 | FAILED_TILE - Chennai/Ennore (tile_4_4) | 20 | 20 |
| S7 | FAILED_TILE - Tuticorin (tile_1_2) | 10 | 10 |
| S8 | FAILED_TILE - other failed regions | 10 | 10 |
| S9 | Very high FRP (>= 5 MW, any coverage) | 5 | 5 |
| S10 | Persistent locations (grid_active_days >= 10) | 5 | 5 |
| **Total** | | **100** | **100** |

**Design rationale for key strata:**

- **S1-S3** ensure coverage of events near HIGHER_RELEVANCE industrial
  facilities at varying proximities — the strongest potential industrial-context cases.
- **S4** includes substation and general industrial zone contexts — important
  because these dominate the OSM dataset (substations = 48.6% of events <= 5 km).
- **S5** provides negative industrial-context control cases from areas
  where OSM data is available but shows no nearby industry.
- **S6-S7** ensure that the most industrially significant failed-tile regions
  (Chennai/Ennore, Tuticorin) are explicitly represented despite having
  no OSM proximity information.
- **S8** covers the remaining 4 failed tiles.
- **S9** ensures high-FRP outliers are represented regardless of industrial context.
- **S10** ensures persistent thermal locations are represented.

---

## 6. Ground Truth Rule - Confirmation

> ALL 100 selected candidates have `ground_truth_status = UNVERIFIED`.
>
> No labels have been assigned from:
> - OSM proximity or facility name
> - WorldCover land cover class
> - FRP or brightness temperature
> - Persistence or grid statistics
> - Heuristic scoring
> - Random Forest predictions

This was verified programmatically. The assertion `all(batch.ground_truth_status == "UNVERIFIED")` passed without error.

---

## 7. Diversity Quality Check - Batch vs. Population

### 7.1 OSM Coverage Status

| Status | Population % | Batch % (n) | Notes |
|---|---:|---:|---|
| COVERED | 51.3% | 56.0% (56) | Slightly over-represented (strata S1-S5) |
| FAILED_TILE | 48.7% | 44.0% (44) | Well represented: 20 Chennai/Ennore, 10 Tuticorin, 10 other |

### 7.2 OSM Relevance Tier

| Tier | Population % | Batch % (n) | Notes |
|---|---:|---:|---|
| HIGHER_RELEVANCE | 39.5% | 63.0% (63) | Intentionally over-represented (S1-S3 explicit strata) |
| GENERAL_CONTEXT | 28.8% | 19.0% (19) | Slightly under-represented |
| CAUTION_LOWER_RELEVANCE | 31.8% | 18.0% (18) | Slightly under-represented |

> **Note on HIGHER_RELEVANCE over-representation:** This is intentional. The
> closest industrial-context matches are the most informative cases for human
> reviewers — they can evaluate whether a HIGHER_RELEVANCE facility at <2 km
> explains the thermal anomaly. The batch is designed for information value,
> not distributional fidelity.

### 7.3 WorldCover Land Cover

| Class | Population % | Batch % (n) |
|---|---:|---:|
| Cropland | 21.0% | 31.0% (31) |
| Tree cover | 21.2% | 24.0% (24) |
| Grassland | 18.2% | 22.0% (22) |
| Built-up | 24.5% | 12.0% (12) |
| Shrubland | 10.9% | 6.0% (6) |
| Bare/sparse vegetation | 3.8% | 3.0% (3) |
| Mangroves | 0.2% | 1.0% (1) |
| Permanent water bodies | 0.3% | 1.0% (1) |

All 8 land cover classes present in the 633-event population are represented
in the batch. Built-up is under-represented (12% vs 25%) because the
geographic-spread selection de-prioritises clustering in the Chennai urban
corridor, where most built-up events are co-located.

### 7.4 Distance Bands

| Threshold | Population % | Batch % (n) |
|---|---:|---:|
| <= 500 m | 19.1% | 17.0% (17) |
| <= 1 km | 23.9% | 26.0% (26) |
| <= 2 km | 29.9% | 37.0% (37) |
| <= 5 km | 44.9% | 48.0% (48) |
| <= 10 km | 50.2% | 56.0% (56) |

Batch slightly over-represents events within 2-10 km, consistent with
the prioritisation of higher-industrial-context cases in S1-S3.

### 7.5 FRP Distribution

| FRP Band | Population % | Batch % (n) | Notes |
|---|---:|---:|---|
| < 1 MW | 30.0% | 11.0% (11) | Under-represented |
| 1-3 MW | 44.7% | 31.0% (31) | Under-represented |
| 3-5 MW | 16.4% | 26.0% (26) | Over-represented |
| >= 5 MW | 8.8% | 32.0% (32) | Intentionally over-represented (S9 stratum + priority weight) |

> **Note on high-FRP over-representation:** High-FRP events are the most
> informative for distinguishing industrial thermal sources from
> agricultural/natural fires. The S9 stratum and priority weighting
> deliberately elevate these events. This is NOT equivalent to labelling
> them as industrial fires.

### 7.6 Persistence

| Active Days | Population % | Batch % (n) |
|---|---:|---:|
| 1 day | 50.6% | 75.0% (75) |
| 2-4 days | 17.5% | 9.0% (9) |
| 5-9 days | 14.8% | 4.0% (4) |
| >= 10 days | 17.1% | 12.0% (12) |

Single-day events are over-represented. This is because the 195 Chennai/Ennore
FAILED_TILE events (stratum S6, 20 selected) include many single-day observations.
Persistent events (>=10 days) are represented at 12%.

### 7.7 Sensor

| Sensor | Population % | Batch % (n) |
|---|---:|---:|
| VIIRS_N20 | 53.9% | 59.0% (59) |
| VIIRS_SUOMI_NPP | 46.1% | 41.0% (41) |

Both sensors are well-represented with near-proportional coverage.

### 7.8 Temporal Distribution

| Month | Population % | Batch % (n) |
|---|---:|---:|
| November 2024 | 22.1% | 31.0% (31) |
| December 2024 | 37.6% | 37.0% (37) |
| January 2025 | 40.3% | 32.0% (32) |

All three months are represented. November is slightly over-represented and
January slightly under-represented, consistent with the geographic-spread
selection choosing more diverse spatial coverage.

### 7.9 Geographic Extent

| | Population | Batch |
|---|---|---|
| Latitude range | [8.139, 13.449] | [8.261, 13.394] |
| Longitude range | [76.519, 80.292] | [76.519, 80.285] |

The batch covers nearly the full geographic extent of the population.

---

## 8. Output Files

### 8.1 validation_candidates_v2.csv (all 633 events)

**Path:** `outputs/ground_truth_investigation/validation_candidates_v2.csv`
**Rows:** 633
**Columns:** 63

Contains all 633 FIRMS events with:
- event_id (FIRMS_TN_XXXX), row_id, acq_date, acq_time, coordinates
- All FIRMS thermal and detection fields
- All 31 baseline feature-engineering outputs (persistence, grid stats, thermal features)
- WorldCover land cover (Step 1)
- OSM proximity context including osm_coverage_status (Step 2-3)
- candidate_priority_score and candidate_priority (HIGH/MEDIUM/LOW)
- is_spatial_duplicate flag
- selection_rationale (human-readable text)
- ground_truth_status = UNVERIFIED for all rows

### 8.2 validation_batch_v1.csv (~100 events)

**Path:** `outputs/ground_truth_investigation/validation_batch_v1.csv`
**Rows:** 100
**Columns:** 63

Sorted by candidate_priority_score descending.
All events have ground_truth_status = UNVERIFIED.
Each event includes a concise selection_rationale describing:
  - OSM context and distance (or coverage failure reason)
  - FRP level
  - Persistence level
  - Land cover class

---

## 9. Limitations and Potential Sampling Bias

1. **OSM coverage bias.** 7/16 retrieval tiles failed. The 44 FAILED_TILE
   events in the batch have no OSM proximity information. Their industrial
   context is genuinely unknown, not absent.

2. **HIGHER_RELEVANCE over-representation (63% vs 40%).** Intentional design
   choice for investigative informativeness. Does not imply these events are
   confirmed industrial sources.

3. **High-FRP over-representation (32% vs 8.8% for >=5 MW).** Intentional.
   High-FRP events are more informative for human reviewers. Does not imply
   industrial origin.

4. **Built-up under-representation (12% vs 25%).** Geographic-spread selection
   avoids clustering multiple events in the Chennai/built-up corridor. Partially
   compensated by S6 FAILED_TILE stratum covering the same region.

5. **Single-day events are more numerous in the batch (75%)** than their
   population share (51%). This is because the FAILED_TILE strata (S6-S8)
   contain predominantly single-observation events from the Nov-Jan window.

6. **Priority score is heuristic.** The component weights (30/25/20/15/10%)
   reflect investigative usefulness judgements, not validated empirical weights.
   Priority is guidance for human reviewers, not a classification.

7. **Spatial deduplication radius (5.5 km).** Some nearby events that represent
   genuinely distinct thermal sources within the same area may be flagged as
   duplicates. Human reviewers should note the is_spatial_duplicate flag.

---

## 10. Scope Confirmation

| Constraint | Status |
|---|---|
| Random Forest retraining | NOT performed |
| Ground-truth labels assigned | NONE |
| Sentinel-2 implemented | NOT implemented |
| 31-feature baseline modified | NOT modified |
| Original 633-event population | PRESERVED INTACT |
| Candidates labelled "confirmed industrial fires" | NEVER |
| Batch described as "balanced" | NOT used - it is DIVERSE |
| FAILED_TILE treated as "no industrial facility" | NO - treated as UNKNOWN |
| Previous Phase 2B and 2C outputs preserved | YES |
