# Human Validation Guide --- FIRMS Thermal Anomaly Dataset

## 1. Purpose of This Validation

This validation is being performed because the current AI pipeline can
detect and describe **thermal anomalies**, but it does not yet have
reliable, independently verified ground-truth labels for those events.

The current dataset contains **633 FIRMS thermal anomaly events** from
Tamil Nadu.

The system already provides supporting context for each event:

-   **NASA FIRMS** --- tells us where and when a satellite-detected
    thermal anomaly occurred, along with measurements such as FRP,
    brightness, time, and sensor.
-   **ESA WorldCover** --- provides the land-cover context around the
    event.
-   **OpenStreetMap (OSM)** --- provides nearby
    industrial/infrastructure context.
-   **Spatial analysis** --- provides distance to nearby OSM objects and
    records whether OSM coverage was successfully retrieved.

These sources help us identify events that *look* industrial,
agricultural, natural, or ambiguous, but they do **not** by themselves
establish the true cause of the event.

### Why are you validating the data?

Your job is to independently investigate selected events and determine
which classification is best supported by available evidence.

This creates a **human-validated reference set** that can later be used
to evaluate and improve the AI system.

Without this step, a model could appear highly accurate simply because
it learned to reproduce the same heuristic rules that were used to
create its training labels.

**Therefore, this validation is not just data cleaning. It is the
process that gives the project an independent basis for evaluating
whether the AI is actually distinguishing industrial thermal events from
other thermal anomalies.**

------------------------------------------------------------------------

# 2. What You Are Validating

You will work primarily with:

`validation_batch_v1.csv`

This contains approximately **100 selected events** from the original
633-event population.

The 100 events were deliberately selected as a **DIVERSE VALIDATION
BATCH**.

They were selected to represent different:

-   industrial proximity levels
-   thermal intensities
-   FRP values
-   persistence patterns
-   WorldCover classes
-   geographic areas
-   dates/seasons
-   VIIRS sensors
-   industrial-context categories
-   agricultural-looking cases
-   natural/vegetation-looking cases
-   ambiguous cases
-   OSM-covered areas
-   areas where OSM retrieval failed

The batch is **not intended to represent a known class distribution**.

Do NOT try to make the final labels balanced.

------------------------------------------------------------------------

# 3. Most Important Rule

## Candidate selection is NOT ground truth.

Every event in the validation batch should initially have:

`ground_truth_status = UNVERIFIED`

Do not assume an event is industrial simply because:

-   it is close to a factory,
-   it is close to a power plant,
-   it is close to a refinery,
-   OSM says it is in an industrial area,
-   WorldCover says it is built-up,
-   FRP is high,
-   the event is persistent,
-   the baseline model predicts Industrial Fire,
-   a heuristic score is high.

These are **clues**, not proof.

Likewise, do not assume an event is agricultural or natural solely
because WorldCover says it is cropland or vegetation.

------------------------------------------------------------------------

# 4. Validation Classes

Use one of the following final classifications:

### 1. Industrial Fire

Use when independent evidence supports an actual fire/event associated
with an industrial facility or industrial operation.

Examples may include evidence of:

-   an industrial facility fire,
-   fire within an industrial complex,
-   fire at an industrial processing/storage location,
-   an industrial incident reported by a reliable source.

### 2. Persistent Industrial Thermal Source

Use when evidence supports a recurring or persistent thermal source
associated with an industrial facility/process rather than a
conventional one-time fire.

Examples may include:

-   recurring thermal emissions associated with an industrial operation,
-   persistent heat associated with a facility,
-   a long-running industrial thermal source.

Do not assign this label merely because FIRMS detected the location on
multiple days. Persistence in FIRMS is supporting evidence only.

### 3. Agricultural Burning

Use when independent evidence supports agricultural
residue/stubble/field burning or another agricultural burning event.

### 4. Natural/Forest Fire

Use when evidence supports a wildfire, forest fire, grassland fire,
vegetation fire, or another natural/non-industrial fire.

### 5. Other/Unclassified

Use when there is enough evidence that the event does not fit the main
industrial/agricultural/natural categories, but it can still be
reasonably classified as another type of thermal event.

### 6. Unknown/Insufficient Evidence

Use when the available evidence is insufficient to make a reliable
classification.

**Do not force a label.**

Unknown is a valid and scientifically useful result.

------------------------------------------------------------------------

# 5. Confidence Rating

For every final classification, assign:

-   **High**
-   **Medium**
-   **Low**

## High confidence

Use when multiple independent pieces of evidence strongly support the
classification.

Example:

-   FIRMS event location matches an industrial facility,
-   independent imagery or official reporting supports the event,
-   timing/location are consistent,
-   no strong contradictory evidence exists.

## Medium confidence

Use when the evidence reasonably supports the classification but some
uncertainty remains.

## Low confidence

Use when the classification is plausible but evidence is limited or
ambiguous.

If evidence is genuinely insufficient, prefer:

`Unknown/Insufficient Evidence`

rather than assigning a low-confidence guess.

------------------------------------------------------------------------

# 6. Evidence Hierarchy

Use independent evidence wherever possible.

A useful evidence priority is:

### Strong evidence

-   Official government/authority records
-   Official incident reports
-   Reliable industrial/company documentation
-   Directly interpretable satellite imagery
-   Multiple independent credible sources agreeing on the event

### Supporting evidence

-   Reputable news reports
-   OSM facility information
-   WorldCover land-cover information
-   FIRMS persistence/FRP/brightness information

### Weak evidence

-   A single unverified web claim
-   Assumptions based only on proximity
-   Assumptions based only on land-cover class
-   Model predictions
-   Heuristic scores

The exact evidence available will vary by event.

Document what you actually found.

------------------------------------------------------------------------

# 7. How to Validate One Event

For each event:

## Step 1 --- Identify the FIRMS event

Record/check:

-   Event ID
-   Date/time
-   Latitude
-   Longitude
-   Sensor
-   FRP
-   brightness/thermal information
-   persistence information

Do not change these source values unless there is a documented data
error.

------------------------------------------------------------------------

## Step 2 --- Check the surrounding land cover

Review the WorldCover information.

Ask:

> What type of environment is around the FIRMS detection?

Examples:

-   cropland
-   forest/tree cover
-   grassland
-   built-up
-   industrial surroundings
-   water
-   bare/sparse vegetation

Remember:

**WorldCover is context, not proof of the fire type.**

------------------------------------------------------------------------

## Step 3 --- Check OSM context

Review:

-   nearest OSM object
-   OSM category
-   relevance tier
-   distance
-   `osm_coverage_status`

Pay particular attention to the relevance tier.

### HIGHER_RELEVANCE

Examples:

-   refinery
-   petrochemical
-   power plant
-   steel/metallurgy
-   cement
-   mining
-   LNG/oil/gas
-   industrial works/factory

### GENERAL_CONTEXT

Examples:

-   industrial area
-   industrial landuse
-   generic industrial building

### CAUTION_LOWER_RELEVANCE

Examples:

-   power substation
-   generic industrial building

### IMPORTANT

A nearby substation does NOT mean the thermal anomaly came from the
substation.

A nearby industrial building does NOT prove an industrial fire.

A failed OSM tile does NOT mean there is no industrial facility nearby.

If:

`osm_coverage_status = FAILED_TILE`

record that limitation explicitly.

------------------------------------------------------------------------

# 8. Independent Investigation

After reviewing the dataset context, investigate the event
independently.

Depending on the event, look for:

-   satellite imagery
-   official government information
-   fire/incident records
-   industrial/company information
-   reputable news reports
-   other credible evidence

Use the coordinates and date/time to make the search as specific as
possible.

For example, search using combinations of:

-   location
-   facility name
-   event date
-   fire/incident
-   industrial facility type

Do not rely on a search result simply because it contains similar words.

Check whether the source actually refers to the same location and event.

------------------------------------------------------------------------

# 9. Satellite Imagery Guidance

Optical satellite imagery such as Sentinel-2 can be useful for
examining:

-   surface conditions,
-   burn scars,
-   vegetation loss,
-   changes before and after an event,
-   field burning patterns,
-   industrial-area surface changes.

### Important limitation

Sentinel-2 SWIR is **not direct thermal-plume evidence**.

Do not write:

> "Sentinel-2 detected the thermal plume."

Instead write something like:

> "Sentinel-2 imagery shows surface change/burn evidence consistent with
> the event."

Also remember that optical imagery may not exist at the exact FIRMS
detection time because of:

-   revisit timing,
-   cloud cover,
-   image availability.

Do not treat absence of a visible change as proof that no event
occurred.

------------------------------------------------------------------------

# 10. Handling OSM FAILED_TILE Events

A significant portion of the validation batch comes from regions where
OSM retrieval failed.

For these events:

`FAILED_TILE` means:

> OSM data could not be successfully retrieved for the relevant tile.

It does **NOT** mean:

> No industrial facility exists there.

This distinction is critical.

Do not classify such an event as non-industrial just because the OSM
facility fields are empty.

Instead, use independent evidence to investigate the area.

------------------------------------------------------------------------

# 11. Conflicting Evidence

Sometimes sources will disagree.

Example:

-   WorldCover = cropland
-   OSM = industrial facility 1 km away
-   FIRMS = persistent detections
-   news = no relevant incident found

Do not automatically choose one source.

Record the conflict.

Consider:

-   source reliability,
-   spatial proximity,
-   temporal relevance,
-   whether the evidence refers to the exact event,
-   whether the evidence is direct or indirect.

If the conflict cannot be resolved, use:

`Unknown/Insufficient Evidence`

or an appropriate lower-confidence classification.

------------------------------------------------------------------------

# 12. What NOT to Do

Do NOT:

-   label an event Industrial Fire solely because OSM is nearby;
-   label an event Agricultural Burning solely because WorldCover is
    cropland;
-   label an event Natural/Forest Fire solely because WorldCover is
    vegetation;
-   label an event Persistent Industrial Thermal Source solely because
    it appears on multiple FIRMS dates;
-   use the Random Forest prediction as ground truth;
-   use a heuristic score as ground truth;
-   force every event into a class;
-   invent an incident when no evidence is available;
-   copy an existing weak label without independently checking it;
-   treat missing OSM data as evidence of no facility;
-   treat a substation as a thermal-emitting facility by default;
-   claim Sentinel-2 SWIR directly detected a thermal plume.

------------------------------------------------------------------------

# 13. Required Validation Record

For each validated event, record:

  Field             What to enter
  ----------------- ------------------------------------------------
  event_id          Existing event ID
  final_label       One of the six approved classes
  confidence        High / Medium / Low
  evidence_source   Main source(s) used
  evidence_date     Date of evidence/event report where applicable
  reviewer          Your name/identifier
  reviewer_notes    Short explanation of reasoning

If the dataset already contains dedicated evidence columns, use those
columns rather than creating unnecessary duplicates.

------------------------------------------------------------------------

# 14. Reviewer Notes --- What a Good Note Looks Like

### Good

> "FIRMS detection is approximately 600 m from a mapped cement facility.
> Independent imagery shows a disturbed/burned surface within the
> facility area around the event period. Evidence supports an
> industrial-related event. Medium confidence."

### Good

> "Event is located over cropland. Independent imagery shows a field
> burn pattern around the event date. No relevant industrial incident
> found. Agricultural Burning, High confidence."

### Good

> "OSM tile failed for this location, so industrial proximity cannot be
> assessed from OSM. Available imagery does not provide sufficient
> evidence to determine the cause. Unknown/Insufficient Evidence."

### Bad

> "Near factory, so Industrial Fire."

### Bad

> "Cropland, therefore Agricultural Burning."

### Bad

> "Model says industrial, so Industrial Fire."

The note should explain **why the evidence supports the final label**.

------------------------------------------------------------------------

# 15. Recommended Validation Procedure

For each event, follow this order:

1.  Open the event record.
2.  Check FIRMS date/time/location.
3.  Check FRP and thermal characteristics.
4.  Check persistence.
5.  Check WorldCover.
6.  Check OSM facility/category/distance.
7.  Check `osm_coverage_status`.
8.  Investigate independent evidence.
9.  Compare evidence from multiple sources.
10. Assign the best-supported label.
11. Assign confidence.
12. Record evidence source/date.
13. Write a concise reviewer note.
14. If evidence is insufficient, use `Unknown/Insufficient Evidence`.

------------------------------------------------------------------------

# 16. Final Principle

The goal is **not** to prove that the AI's current prediction is
correct.

The goal is to determine what the evidence actually supports.

You are acting as an **independent reviewer**, not as someone trying to
confirm the model.

If the model/heuristics appear wrong, record the evidence and assign the
correct label.

If the evidence is unclear, record:

`Unknown/Insufficient Evidence`

That is a successful validation outcome.

------------------------------------------------------------------------

## Summary

The project currently has:

**633 FIRMS thermal anomalies**

↓

**\~100 carefully selected diverse validation candidates**

↓

**Human investigation**

↓

**Independent evidence**

↓

**Ground-truth labels + confidence**

↓

**Future AI evaluation**

The validated subset will eventually allow the project team to answer
the most important question:

> **Does the AI actually distinguish industrial thermal events from
> agricultural, natural, and other thermal anomalies --- or is it merely
> reproducing our initial heuristics?**
