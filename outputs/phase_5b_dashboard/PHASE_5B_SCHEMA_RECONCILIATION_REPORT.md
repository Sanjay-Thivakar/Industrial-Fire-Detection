# PHASE 5B — SCHEMA RECONCILIATION REPORT

**Document purpose:** Resolve the 57 vs 61 column discrepancy reported after Step 2.
**Audit date:** 2026-09-06
**Files inspected (read-only):**
- `outputs/phase_5b_dashboard/dashboard_events_633.csv`
- `outputs/phase_5b_dashboard/dashboard_schema_design.md`
- `outputs/phase_5b_dashboard/_build_dashboard.py`

---

## FINDING SUMMARY

> **The "57 vs 61" discrepancy is a documentation arithmetic error in the schema design header — not a build error.**
>
> The actual data tables inside `dashboard_schema_design.md` define exactly **61 fields**, which are the same 61 fields in `dashboard_events_633.csv`. There is zero difference between the approved schema tables and the built CSV.

---

## 1. COLUMN LIST: dashboard_events_633.csv (61 columns, in order)

| # | Field | Group |
|---|-------|-------|
| 1 | `event_id` | A — Identity |
| 2 | `row_id` | A — Identity |
| 3 | `acq_date` | A — Identity |
| 4 | `acq_time` | A — Identity |
| 5 | `acq_datetime` | A — Identity |
| 6 | `daynight` | A — Identity |
| 7 | `latitude` | B — Location |
| 8 | `longitude` | B — Location |
| 9 | `satellite` | C — FIRMS Thermal |
| 10 | `instrument` | C — FIRMS Thermal |
| 11 | `firms_confidence` | C — FIRMS Thermal |
| 12 | `frp` | C — FIRMS Thermal |
| 13 | `brightness` | C — FIRMS Thermal |
| 14 | `bright_t31` | C — FIRMS Thermal |
| 15 | `brightness_difference` | C — FIRMS Thermal |
| 16 | `is_day` | C — FIRMS Thermal |
| 17 | `is_stubble_burning_season` | C — FIRMS Thermal |
| 18 | `grid_detection_count` | C — FIRMS Thermal |
| 19 | `grid_active_days` | C — FIRMS Thermal |
| 20 | `persistent_location_flag` | C — FIRMS Thermal |
| 21 | `grid_total_frp` | C — FIRMS Thermal |
| 22 | `high_frp_flag_local` | C — FIRMS Thermal |
| 23 | `brightness_zscore_local` | C — FIRMS Thermal |
| 24 | `predicted_class` | D — ML Prediction |
| 25 | `probability_agricultural_burning` | D — ML Prediction |
| 26 | `probability_industrial_thermal_activity` | D — ML Prediction |
| 27 | `probability_natural_wildfire_other` | D — ML Prediction |
| 28 | `max_probability` | D — ML Prediction |
| 29 | `ml_confidence` | D — ML Prediction |
| 30 | `osm_coverage_status` | E — OSM Context |
| 31 | `nearest_facility_name` | E — OSM Context |
| 32 | `nearest_facility_type` | E — OSM Context |
| 33 | `nearest_facility_category` | E — OSM Context |
| 34 | `nearest_facility_tier` | E — OSM Context |
| 35 | `distance_to_facility_m` | E — OSM Context |
| 36 | `near_industrial_500m` | E — OSM Context |
| 37 | `near_industrial_1000m` | E — OSM Context |
| 38 | `near_industrial_2000m` | E — OSM Context |
| 39 | `nearest_hr_category` | E — OSM Context |
| 40 | `nearest_hr_name` | E — OSM Context |
| 41 | `distance_to_higher_relevance_m` | E — OSM Context |
| 42 | `landcover_code` | F — WorldCover |
| 43 | `landcover_class` | F — WorldCover |
| 44 | `pre_observation_status` | G — Sentinel-2 |
| 45 | `post_observation_status` | G — Sentinel-2 |
| 46 | `s2_change_status` | G — Sentinel-2 |
| 47 | `selected_pre_image_date` | G — Sentinel-2 |
| 48 | `selected_post_image_date` | G — Sentinel-2 |
| 49 | `s2_pre_feature_status` | G — Sentinel-2 |
| 50 | `s2_post_feature_status` | G — Sentinel-2 |
| 51 | `s2_pre_ndvi_mean` | G — Sentinel-2 |
| 52 | `s2_post_ndvi_mean` | G — Sentinel-2 |
| 53 | `s2_dnbr_mean` | G — Sentinel-2 |
| 54 | `has_human_validation` | H — Human Validation |
| 55 | `human_validation_status` | H — Human Validation |
| 56 | `human_ground_truth_class` | H — Human Validation |
| 57 | `is_unambiguous_ground_truth` | H — Human Validation |
| 58 | `inference_timestamp` | I — Provenance |
| 59 | `model_version` | I — Provenance |
| 60 | `model_sha256` | I — Provenance |
| 61 | `data_source_version` | I — Provenance |

---

## 2. FIELDS IN THE APPROVED SCHEMA DESIGN

Parsing the data dictionary tables embedded in `dashboard_schema_design.md` yields **exactly 61 fields** (fields 1–61 above). Every field in the CSV appears in the schema design tables. Zero fields are missing. Zero fields are extra.

---

## 3. COMPARISON

| Metric | Value |
|--------|-------|
| Fields in `dashboard_events_633.csv` | **61** |
| Fields in schema design **tables** | **61** |
| Fields in CSV but NOT in schema tables | **0** |
| Fields in schema tables but NOT in CSV | **0** |
| Duplicate fields in CSV | **0** |
| Alias/renamed fields | **2** (`firms_confidence` ← `confidence`; `ml_confidence` ← `confidence.1`) |
| CSV list identical to build script DASHBOARD_COLS list | **Yes** |

**Conclusion:** There is no actual discrepancy. The CSV, build script, and schema design data tables are in complete agreement at 61 fields.

---

## 4. ROOT CAUSE OF THE "57 vs 61" CONFUSION

The "57" figure appears in exactly one place: the **"RECOMMENDED FINAL SCHEMA"** summary block at the top of `dashboard_schema_design.md`:

```
**Total fields: 57** across 9 logical groups.
GROUP A  — Event Identity         (6 fields)
GROUP B  — Location               (2 fields)
GROUP C  — FIRMS Thermal Evidence (15 fields)
GROUP D  — ML Prediction          (6 fields)
GROUP E  — OSM Context            (12 fields)
GROUP F  — WorldCover             (2 fields)
GROUP G  — Sentinel-2             (10 fields)
GROUP H  — Human Validation       (7 fields)    ← says 7
GROUP I  — Provenance             (5 fields)    ← says 5
```

**This summary block contains THREE arithmetic errors:**

| Group | Summary Block Claims | Actual Table Count | Difference |
|-------|---------------------|--------------------|------------|
| A | 6 | 6 | ✅ correct |
| B | 2 | 2 | ✅ correct |
| C | 15 | 15 | ✅ correct |
| D | 6 | 6 | ✅ correct |
| E | 12 | 12 | ✅ correct |
| F | 2 | 2 | ✅ correct |
| G | 10 | 10 | ✅ correct |
| **H** | **7** | **4** | ❌ overcounts by 3 |
| **I** | **5** | **4** | ❌ overcounts by 1 |
| **Total** | **65 (displayed as 57)** | **61** | ❌ also wrong arithmetic |

**Group H discrepancy (7 claimed, 4 in table):**
The summary block counts 7, but the Group H data table only defines 4 fields:
`has_human_validation`, `human_validation_status`, `human_ground_truth_class`, `is_unambiguous_ground_truth`.
The schema design narrative for Group H also lists several fields as *intentionally omitted* (e.g., `human_review_confidence`, `human_raw_label`, `human_validation_notes`, `human_industry_observation`, `ml_training_eligible`). It appears 3 omitted fields were accidentally counted in the summary.

**Group I discrepancy (5 claimed, 4 in table):**
The summary block counts 5, but the Group I data table defines 4 fields:
`inference_timestamp`, `model_version`, `model_sha256`, `data_source_version`.
The fifth field (`model_path`) was explicitly excluded from the schema design — but was accidentally counted in the summary.

**The "57" total is also wrong by the schema's own arithmetic:**
6+2+15+6+12+2+10+7+5 = **65** (not 57). The "57" figure was never correct even by the summary block's own internal numbers.

**The actual correct count from the data tables is 61** — and that is what was built.

---

## 5. THE 4 "ADDITIONAL" FIELDS vs THE CORRECT 57/61 BASELINE

Since the data tables (not the header) define the schema, there are **no "4 additional fields"** — this framing was based on the erroneous "57" header claim. All 61 fields were present in the schema design tables from Step 1.

However, for completeness, the fields numbered 58–61 (which exceed the erroneous "57" count) are:

| Field | Source | Meaning | Frontend Useful? | Keep? |
|-------|--------|---------|-----------------|-------|
| `inference_timestamp` | PRED | UTC datetime of the production inference run | ✅ Yes — "About" / metadata panel | ✅ Keep |
| `model_version` | PRED | Model artifact identifier string | ✅ Yes — reproducibility/audit | ✅ Keep |
| `model_sha256` | PRED | SHA-256 hash of the production model file | ✅ Yes — audit trail | ✅ Keep |
| `data_source_version` | Derived constant | Source dataset version tag | ✅ Yes — lineage tracking | ✅ Keep |

All four are genuine provenance fields explicitly described in the Group I section of the schema design. None were introduced by error. None are synthetic or leakage risks.

---

## 6. WAS THE INTEGRITY CHECK INCORRECT?

**Yes — but only in its reported expectation, not in its outcome.**

The Step 2 build script set:

```python
chk(len(df.columns) == len(DASHBOARD_COLS), 'CHECK 4: All 57 approved columns present', ...)
```

- `len(DASHBOARD_COLS)` = **61** (the actual build list)
- `len(df.columns)` = **61**
- Result: PASS (61 == 61) ✅

The check label said "57 approved columns" but evaluated against 61. This means:

- **The check correctly validated that all 61 intended columns were present** — the validation logic was sound.
- **The check label was misleading** — it should have said "61 approved columns" to match the evaluation.
- **The CSV content is correct** — it was built from and validated against the 61-field `DASHBOARD_COLS` list, which derives from the Step 1 schema data tables.

---

## 7. FINAL RECOMMENDATION

The 61-field schema is the correct and complete schema. No rebuild is required.

**Corrected group counts:**

| Group | Name | Correct Count |
|-------|------|--------------|
| A | Event Identity | 6 |
| B | Location | 2 |
| C | FIRMS Thermal Evidence | 15 |
| D | ML Prediction | 6 |
| E | OSM Context | 12 |
| F | WorldCover | 2 |
| G | Sentinel-2 | 10 |
| H | Human Validation | **4** (not 7) |
| I | Provenance | **4** (not 5) |
| **Total** | | **61** |

**Recommended action (Step 4):** Update the summary block in `dashboard_schema_design.md` to reflect the correct counts (61 total, H=4, I=4). No changes to `dashboard_events_633.csv` are required.

---

## SCHEMA STATUS

```
REVISED SCHEMA REQUIRED
```

> Not because the CSV is wrong — it is correct — but because the schema design document
> (`dashboard_schema_design.md`) contains an erroneous summary header claiming "57 fields"
> with incorrect group counts for Groups H and I.
>
> **The approved and correct field count is 61.**
> The schema design document header must be corrected to match the 61-field data tables
> that were actually approved and built.
>
> `dashboard_events_633.csv` requires **no changes**.

---

*Read-only reconciliation — no files modified.*
