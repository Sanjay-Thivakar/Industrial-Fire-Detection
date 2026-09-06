# VALIDATION_PROTOCOL_V1.md
# Human Validation Protocol for FIRMS Thermal Anomaly Classification

**Version:** 1.0
**Date:** 2026-09-02
**Project:** SIH — Satellite-Based Industrial Fire Detection, Tamil Nadu
**Applies to:** validation_batch_v1.csv (~100 FIRMS events)

---

## PART A: BEFORE YOU START — CRITICAL PRINCIPLES

### A.1 Why Human Validation Is Necessary

This project detects satellite-observed thermal anomalies using NASA FIRMS
(Fire Information for Resource Management System). FIRMS data indicates that
a thermal anomaly was observed at a specific location and time. It does NOT
by itself identify the cause.

A FIRMS thermal event could represent:

- An **industrial fire** — an uncontrolled fire at an industrial facility
- A **persistent industrial thermal source** — a legitimate continuous heat
  source such as a power plant, smelter, or cement kiln
- **Agricultural burning** — crop residue burning after harvest
- A **natural/forest fire** — wildfire in forest, scrubland, or grassland
- **Another thermal event** — a cooking fire, municipal waste burning,
  road surfacing, or any other heat source

The project's initial model was trained using **weak / heuristic labels**
derived from land cover, OSM proximity, and persistence patterns — NOT from
independently verified ground truth. A model that scores well against weak
labels does NOT necessarily have real-world classification accuracy.

**The human validation set is being created to provide an independent
reference against which future model predictions can eventually be evaluated.**

> **CANDIDATE SELECTION IS NOT GROUND TRUTH.**
>
> An event being included in this validation batch, or having a HIGH
> candidate priority, does NOT mean it is classified as an industrial fire.
> Priority indicates investigative usefulness, not ground-truth class.

---

### A.2 Six Validation Classes

Assign exactly ONE class to each validated event.

---

#### Class 1: Industrial Fire

An uncontrolled, accidental, or emergency fire that occurred at or
originated from an industrial facility.

**Indicators (any combination):**
- Official incident records (fire department, pollution control board,
  company disclosure)
- News reports with verifiable facts (facility name, date, location)
- Visible fire damage, smoke plume, or burn scar in satellite imagery
  matching the FIRMS event location and date
- FRP significantly elevated above the facility's normal baseline

**Decision guidance:**
Use this class ONLY when there is clear independent evidence of an
uncontrolled fire event at a specific facility. Mere OSM proximity is
insufficient.

---

#### Class 2: Persistent Industrial Thermal Source

A **legitimate, continuous or recurring** industrial heat emission.
This is NOT a fire — it is normal industrial operation (e.g. a power plant
boiler, cement kiln, steel furnace, or gas flare).

**Indicators (any combination):**
- The FIRMS location is consistent with a known operating industrial
  facility (verified by independent source, not only OSM proximity)
- The detection recurs over many days (grid_active_days >= 5) at the same
  grid location
- Thermal intensity is consistent with operational levels (moderate,
  stable FRP) rather than a fire spike
- No report of fire or emergency at the facility on the event date

**Decision guidance:**
Persistence alone is not sufficient. Many agricultural burning events also
recur over days. A combination of persistence, facility confirmation, and
no emergency evidence is required.

---

#### Class 3: Agricultural Burning

Deliberate burning of crop residue, field stubble, or agricultural waste.

**Indicators (any combination):**
- WorldCover class is Cropland, Grassland, or similar agricultural land
- FIRMS event occurs during known burning seasons (post-harvest: Oct–Jan in
  Tamil Nadu)
- Spatial pattern consistent with field burning (linear or clustered events
  matching field boundaries visible in imagery)
- Local news or agricultural reports of burning in the area

**Decision guidance:**
Do NOT classify an event as Agricultural Burning merely because WorldCover
class is Cropland. Many areas with industrial or other fires also have
adjacent cropland. Seasonal context and independent evidence strengthen this
classification.

---

#### Class 4: Natural/Forest Fire

An uncontrolled fire in natural vegetation — forest, scrubland, grassland,
or wetland — not attributable to agriculture or industry.

**Indicators (any combination):**
- WorldCover class is Tree cover, Shrubland, Grassland, or Mangroves
- Fire/forest department records or news reports of wildfires in the area
- Visible burn scar in satellite imagery with no adjacent agricultural or
  industrial context
- Event occurs in dry season or during documented fire weather conditions

**Decision guidance:**
Do NOT classify an event as Natural/Forest Fire merely because WorldCover
shows vegetation. Industrial fires and agricultural fires also occur in and
near vegetated areas. Independent evidence of a natural ignition source or
spread pattern is required.

---

#### Class 5: Other/Unclassified

The event has a clearly identifiable cause that does NOT fit Classes 1–4.

**Examples:**
- Municipal waste burning or dump fire
- Road or building construction activity
- Cooking fires in dense settlements
- Other heat sources with identified but non-industrial, non-agricultural,
  non-natural cause

**Decision guidance:**
Use this class when you can positively identify the cause as something
specific but outside the other four classes. Provide a description in
reviewer notes.

---

#### Class 6: Unknown/Insufficient Evidence

The available evidence is insufficient to confidently assign any of the
above classes.

**Use this class when:**
- No independent evidence was found for this event
- Available evidence is contradictory
- OSM coverage failed (FAILED_TILE) and no alternative information is
  available
- Cloud cover prevents optical imagery interpretation
- The FIRMS signal is weak or marginal and cannot be confirmed

**Decision guidance:**
Unknown/Insufficient Evidence is a valid and acceptable outcome. Do NOT
force an event into a class to avoid using this label. Honest uncertainty
is more valuable than a confident wrong answer.

---

### A.3 Confidence Levels

Assign exactly ONE confidence level to each validated event.

| Level | Definition |
|---|---|
| **High** | Strong, direct, independent evidence supports the classification. Multiple credible sources agree. The reviewer is confident that an independent reviewer would reach the same conclusion. |
| **Medium** | Reasonable supporting evidence exists but some uncertainty remains. For example: consistent land-cover + seasonal context + partially corroborating news, but no official record. |
| **Low** | The classification is the most plausible given available information, but evidence is sparse, indirect, or not fully verified. Another interpretation is possible. |

**Important:** Confidence describes the strength of your evidence, NOT the
probability that the project's model is correct. A High-confidence
"Unknown/Insufficient Evidence" label is valid and appropriate when you are
certain that evidence is genuinely unavailable.

---

## PART B: EVIDENCE HIERARCHY

When reviewing an event, use and document evidence according to the
following hierarchy. Higher-value evidence takes precedence.

### B.1 HIGH-VALUE EVIDENCE (primary — seek this first)

- Official government or regulatory records (Tamil Nadu Pollution Control
  Board, fire departments, Ministry of Environment)
- Official industrial incident reports or company safety disclosures
- Forest department or disaster management authority records
- Multiple corroborating high-quality sources
- Directly interpretable satellite imagery clearly showing fire, smoke
  plume, or burn scar at the FIRMS location on or near the event date

### B.2 SUPPORTING EVIDENCE (use to corroborate, not as sole basis)

- Reputable news reports (regional or national newspapers, verified
  journalists) — note publication name, date, and URL
- OpenStreetMap facility information (name, type, operator if known)
- WorldCover land-cover classification
- FIRMS FRP, brightness temperature, and persistence data
- Seasonal/agricultural burning calendar

### B.3 WEAKER EVIDENCE (use with caution, document limitations)

- A single unverified web claim or social media post
- Proximity to an OSM-mapped industrial facility alone
- WorldCover class alone
- Land-cover assumptions without corroborating evidence
- Model prediction scores or heuristic candidate priority
- Absence of evidence in one source (e.g. no news report) does not prove
  the event did not occur

---

## PART C: UNDERSTANDING THE DATASET FIELDS

### C.1 FIRMS Data Fields

| Field | Meaning |
|---|---|
| `latitude`, `longitude` | WGS84 coordinates of the FIRMS detection (centre of VIIRS pixel, ~375 m resolution) |
| `acq_date`, `acq_time` | Acquisition date (UTC) and time (HHMM UTC) |
| `frp` | Fire Radiative Power in megawatts (MW) — intensity of the detected thermal anomaly |
| `brightness` | Top-of-atmosphere brightness temperature in channel I4 (~3.74 μm) in Kelvin |
| `bright_t31` | Brightness temperature in channel I5 (~11.45 μm) — background thermal channel |
| `brightness_difference` | Difference between I4 and I5 brightness — elevated values suggest active combustion |
| `confidence` | FIRMS detection confidence: h (high), n (nominal), l (low), or numeric percent |
| `satellite_source` | VIIRS_N20 or VIIRS_SUOMI_NPP |
| `daynight` | D = daytime detection, N = nighttime |

**FIRMS is evidence that a thermal anomaly was detected. It is NOT by itself
proof of the cause or classification.**

A high FRP does not confirm an industrial fire. A low FRP does not rule one
out. FRP depends on fire intensity, atmospheric conditions, pixel-level
contamination, and sensor characteristics.

### C.2 Persistence Fields

| Field | Meaning |
|---|---|
| `grid_active_days` | Number of unique days this 0.01-degree grid cell had a FIRMS detection in the observation window |
| `grid_detection_count` | Total FIRMS detections in this grid cell |
| `persistent_location_flag` | 1 if grid_active_days meets the persistence threshold, 0 otherwise |

**Persistence is supporting context, not ground truth.** Industrial thermal
sources typically produce persistent detections, but agricultural burning and
forest fires can also persist for days or weeks. Isolated single-day events
could be either industrial fires or agricultural burns.

### C.3 WorldCover Field

| Field | Meaning |
|---|---|
| `landcover_class` | ESA WorldCover 2021 land-cover classification at the FIRMS event location |

**WorldCover is supporting context only.**

Do NOT classify as Agricultural Burning solely because `landcover_class = Cropland`.
Do NOT classify as Natural/Forest Fire solely because `landcover_class = Tree cover`.

Industrial facilities are often surrounded by agricultural or vegetated land.
A FIRMS event in cropland near a refinery could be either agricultural burning
or an industrial fire — it requires independent investigation.

Available land-cover classes in this dataset:

- Built-up
- Cropland
- Tree cover
- Grassland
- Shrubland
- Bare/sparse vegetation
- Mangroves
- Permanent water bodies

### C.4 OSM Context Fields

| Field | Meaning |
|---|---|
| `osm_coverage_status` | COVERED = OSM data available; FAILED_TILE = OSM retrieval failed (see C.5) |
| `nearest_facility_name` | Name of nearest OSM-mapped industrial object (may be empty) |
| `nearest_facility_category` | Semantic category (e.g. "Power Plant", "Mining & Quarry") |
| `nearest_facility_tier` | Relevance tier: HIGHER_RELEVANCE, GENERAL_CONTEXT, or CAUTION_LOWER_RELEVANCE |
| `distance_to_facility_m` | Geodesic distance to nearest OSM object in metres (Haversine) |
| `distance_to_higher_relevance_m` | Distance to nearest HIGHER_RELEVANCE facility specifically |

**OSM proximity is supporting context only.**

A nearby industrial facility does NOT prove that the FIRMS anomaly originated
from that facility. A nearby power substation (CAUTION_LOWER_RELEVANCE) does
NOT indicate a thermal emission source — substations appear frequently in OSM
and are classified at the lowest relevance tier for this reason.

**OSM Relevance Tiers:**

| Tier | Includes |
|---|---|
| HIGHER_RELEVANCE | Refineries, petrochemicals, power plants, steel/metallurgy, cement plants, mining/quarries, LNG/oil/gas, industrial works |
| GENERAL_CONTEXT | Industrial areas (landuse=industrial), generic industrial buildings, industrial zones |
| CAUTION_LOWER_RELEVANCE | Power substations, electrical infrastructure, warehouses, depots |

### C.5 OSM Failed-Tile Handling

When `osm_coverage_status = FAILED_TILE`:

- The OSM retrieval failed for the geographic tile covering this event.
- This means OSM data is **unavailable**, NOT that no industrial facility exists.
- The `distance_to_facility_m` value for these events is unreliable — it measures
  the distance to the nearest facility from a **different tile**, which may be
  tens to hundreds of kilometres away.
- Do NOT use missing OSM data as evidence for a non-industrial classification.

**Affected regions with FAILED_TILE status in this dataset:**
- Chennai / Manali / Ennore coast (tile_4_4) — India's densest petrochemical
  and power-generation corridor in Tamil Nadu
- Tuticorin (tile_1_2) — major port, SPIC chemicals, Sterlite, Tuticorin Thermal
  Power Station
- Western Coimbatore, Vellore-Tiruvannamalai, other areas

When reviewing FAILED_TILE events, explicitly note "OSM coverage unavailable
for this region — industrial context unknown from OSM" in your reviewer notes.

### C.6 Distance Thresholds

This project evaluated events within:

- <= 500 m from nearest OSM industrial object
- <= 1 km
- <= 2 km (current baseline contextual threshold)
- <= 5 km
- <= 10 km

**Important:** The 2 km threshold is a contextual baseline, not a rule.

> "Within 2 km of an industrial facility" DOES NOT mean "Industrial Fire."

Proximity is one supporting factor among many. An event 300 m from a power
plant with no fire report could be agricultural burning in adjacent cropland.
An event 4 km from a refinery with official fire department records could be
an industrial fire.

---

## PART D: OPTICAL SATELLITE IMAGERY GUIDANCE

Optical satellite imagery (e.g. Sentinel-2, Landsat, Google Earth) may
provide useful independent evidence when cloud-free imagery is available
close to the event date.

**Imagery may help identify:**
- Burn scars or charred vegetation near the event location
- Agricultural field patterns and stubble burning signatures
- Smoke plumes visible in optical bands
- Changes to industrial facility surfaces (fire damage, new structures)
- Vegetation loss

**Important limitations:**
- Optical imagery is NOT the same as the FIRMS thermal detection. FIRMS uses
  thermal-infrared channels. Optical imagery uses visible/near-infrared.
- Sentinel-2 has a revisit time of ~5 days. The exact overpass date may not
  match the FIRMS event date.
- Cloud cover may obscure the area entirely.
- The absence of a visible burn scar does NOT prove that no fire occurred —
  many fire types leave minimal optical signatures.
- Do NOT describe Sentinel-2 SWIR as "direct thermal-plume detection."

**To access imagery:**
- Copernicus Browser (browser.dataspace.copernicus.eu) — Sentinel-2 imagery
- Google Earth Engine or Google Earth — historical imagery
- NASA Worldview (worldview.earthdata.nasa.gov) — MODIS/VIIRS imagery with
  FIRMS overlay

When using imagery as evidence, record the satellite, acquisition date, and
what you observed.

---

## PART E: STEP-BY-STEP REVIEW PROCEDURE

For each event in validation_batch_v1.csv, follow these steps in order:

**Step 1 — Open the event record**
Load the event from validation_batch_v1.csv. Note the event_id, acq_date,
acq_time (UTC), latitude, longitude, and candidate_priority.

**Step 2 — Verify FIRMS date/time/location**
Confirm the coordinates and date are reasonable for Tamil Nadu
(lat 8–14 N, lon 76–81 E, Nov 2024–Jan 2025). Note if the event is
daytime (D) or nighttime (N) — nighttime industrial sources are more
distinctive.

**Step 3 — Review FRP and thermal characteristics**
Check:
- `frp` — very high FRP (>= 10 MW) is unusual and warrants investigation
- `brightness_difference` — high values suggest active combustion
- `confidence` — high (h) confidence events are more reliable detections

**Step 4 — Review persistence**
Check `grid_active_days` and `persistent_location_flag`. A location that
recurs for many days is more consistent with a persistent industrial source
or an extended agricultural/forest fire.

**Step 5 — Review WorldCover**
Note `landcover_class`. Use as context, not as classification basis alone.

**Step 6 — Review OSM context**
Check `osm_coverage_status`. If COVERED:
  - Note `nearest_facility_category`, `nearest_facility_tier`, `distance_to_facility_m`
  - A HIGHER_RELEVANCE facility within 500 m is a meaningful proximity signal
    that warrants further investigation
  - A CAUTION_LOWER_RELEVANCE facility (substation) nearby is less significant

If FAILED_TILE: note the coverage gap in your review notes.

**Step 7 — Check selection rationale**
Read `selection_rationale` to understand why this event was included.
This is NOT a classification — it is context for your investigation.

**Step 8 — Investigate independent evidence**
Search for:
  - News reports for the date and location (e.g. "[city name] fire [date]")
  - Tamil Nadu Pollution Control Board notices
  - State disaster management records
  - Company/facility safety reports
  - Satellite imagery for the event date (+/- 5 days for Sentinel-2)

Start with high-value evidence (official records) before secondary sources.

**Step 9 — Compare evidence from multiple sources**
Do the evidence sources agree? Are they consistent with the FIRMS data?
Note any contradictions.

**Step 10 — Assign the best-supported classification**
Select the class (1–6) best supported by the available evidence.
If evidence is insufficient, select Class 6: Unknown/Insufficient Evidence.

**Step 11 — Assign confidence**
Select High, Medium, or Low based on the quality and consistency of your
evidence.

**Step 12 — Record evidence source and date**
Document what independent evidence you used, including URLs and access dates
where possible.

**Step 13 — Write reviewer notes**
Write concise notes (1–5 sentences) explaining your reasoning. See Part F
for examples.

**Step 14 — Final check**
Confirm that your classification is based on independent evidence, not solely
on OSM proximity, WorldCover, FRP, or the candidate priority score.

---

## PART F: REVIEWER NOTE EXAMPLES

### F.1 Good notes — Industrial Fire

> "FIRMS event at 11.27 N, 77.49 E on 2024-12-14. Located 420 m from an
> OSM-mapped power plant (HIGHER_RELEVANCE). A news report from The Hindu
> (14 Dec 2024) confirms a transformer fire at the Mettur power station on
> this date. FRP = 8.3 MW, nighttime detection, persistent_location_flag = 0
> (single event). Classification: Industrial Fire. Confidence: High."

### F.2 Good notes — Persistent Industrial Thermal Source

> "FIRMS event at 10.96 N, 78.22 E. Grid_active_days = 18. Nearest HIGHER_RELEVANCE
> facility is a power plant at 680 m. No emergency reports found for this date.
> Operational records for the facility indicate continuous generation at this
> period. Consistent thermal pattern over 18 days with stable moderate FRP
> (~3–5 MW) is inconsistent with a fire event. Classification: Persistent
> Industrial Thermal Source. Confidence: Medium — independent operational
> confirmation not directly available, inferred from stability pattern."

### F.3 Good notes — Agricultural Burning

> "FIRMS event at 10.52 N, 79.33 E. WorldCover: Cropland. Acquired 2024-11-22,
> daylight. No OSM industrial facilities within 10 km (COVERED tile). FRP = 1.1 MW,
> single-day detection. Sentinel-2 imagery from 2024-11-25 shows stubble burning
> pattern in paddy fields visible in the area. No news reports of industrial
> incident. Classification: Agricultural Burning. Confidence: Medium — imagery
> is 3 days post-event, pattern is consistent."

### F.4 Good notes — Unknown/Insufficient Evidence

> "FIRMS event at 12.68 N, 80.17 E. osm_coverage_status = FAILED_TILE
> (Chennai/Ennore coast). No OSM facility information available. FRP = 2.4 MW,
> single detection. No news reports found for this date and location. Cloud
> cover in Sentinel-2 imagery for the period prevents optical confirmation.
> The Ennore region contains active heavy industry but OSM data is unavailable
> and no independent verification was possible. Classification:
> Unknown/Insufficient Evidence. Confidence: High — confident that evidence
> is genuinely insufficient given OSM gap and no independent source found."

### F.5 Good notes — FAILED_TILE with investigation attempted

> "FIRMS event at 8.79 N, 77.81 E. osm_coverage_status = FAILED_TILE
> (Tuticorin region). OSM industrial context unavailable. FRP = 5.7 MW,
> nighttime detection. Tuticorin is known to host SPIC, Sterlite Copper
> (now Vedanta), and Tuticorin Thermal Power Station. A search for news
> reports on 2025-01-05 in Tuticorin found no specific fire incident report
> matching this location. WorldCover: Built-up. Cannot confirm or rule out
> industrial cause. Classification: Unknown/Insufficient Evidence. Confidence:
> Medium — the location is consistent with an industrial area but no specific
> incident evidence found."

---

## PART G: REQUIRED VALIDATION FIELDS

Complete these fields for each reviewed event. Use the CSV column names
from validation_batch_v1.csv where they exist:

| CSV Column | Required | Description |
|---|---|---|
| `event_id` | Yes | Event identifier (FIRMS_TN_XXXX) — do not modify |
| `acq_date` | Yes | Acquisition date — do not modify |
| `latitude`, `longitude` | Yes | Coordinates — do not modify |
| `candidate_priority` | Yes | Pre-assigned priority — do not modify |
| `ground_truth_status` | Yes | **SET TO FINAL CLASS after review** |
| `validation_label` | Yes | Short label string matching the class name exactly |
| `validation_confidence` | Yes | High / Medium / Low |
| `validation_notes` | Yes | Reviewer notes (concise, evidence-based) |

Add additional columns as needed:

| New Column | Description |
|---|---|
| `evidence_source` | Name and URL/reference of primary independent evidence |
| `evidence_date` | Date the evidence was accessed or published |
| `reviewer_name` | Name/ID of the reviewer |
| `review_date` | Date the review was completed |

**Valid values for `ground_truth_status` / `validation_label` after review:**

```
Industrial Fire
Persistent Industrial Thermal Source
Agricultural Burning
Natural/Forest Fire
Other/Unclassified
Unknown/Insufficient Evidence
```

---

## PART H: GROUND-TRUTH RULES

The following are NOT sufficient by themselves to establish ground truth:

| Evidence Type | Sufficient Alone? | Notes |
|---|---|---|
| OSM proximity (any distance) | NO | Proximity is context only |
| WorldCover land-cover class | NO | Context only |
| FIRMS FRP or brightness | NO | Thermal intensity does not determine cause |
| FIRMS persistence | NO | Persistence is consistent with multiple classes |
| Heuristic candidate priority score | NO | Priority is investigative ranking, not ground truth |
| Random Forest prediction | NO | Based on weak labels — not verified |
| Absence of news report | NO | Does not prove event did not occur |
| OSM substation nearby | NO | Substations are CAUTION_LOWER_RELEVANCE |

Ground truth should be based on **independent human-reviewed evidence**
from credible sources. When sources conflict, document the conflict and
assign the most defensible classification at the appropriate confidence level.

---

## PART I: ANTI-PATTERNS — WHAT NOT TO DO

- **Do NOT** write: "Industrial Fire because it is within 2 km of a power plant."
- **Do NOT** write: "Agricultural Burning because WorldCover is Cropland."
- **Do NOT** write: "Natural Fire because WorldCover is Tree cover."
- **Do NOT** write: "Not industrial because OSM data is missing."
- **Do NOT** write: "Classified as industrial because the priority is HIGH."
- **Do NOT** assign a class without documenting what independent evidence
  was found (or explicitly noting that none was found).
- **Do NOT** treat the absence of a finding as proof of absence.

---

## PART J: QUICK REFERENCE CARD

```
VALIDATION CLASSES             CONFIDENCE LEVELS
1. Industrial Fire             High   — strong direct evidence
2. Persistent Industrial       Medium — reasonable, some uncertainty
   Thermal Source              Low    — most plausible, limited evidence
3. Agricultural Burning
4. Natural/Forest Fire         DECISION RULE
5. Other/Unclassified          Independent evidence required.
6. Unknown/Insufficient        OSM/WorldCover/FRP alone
   Evidence (valid outcome)    = insufficient for ground truth.

FAILED_TILE = OSM data missing. NOT "no industry here."
CANDIDATE SELECTION IS NOT GROUND TRUTH.
```

---

*End of VALIDATION_PROTOCOL_V1.md*
