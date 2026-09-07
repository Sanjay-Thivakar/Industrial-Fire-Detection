# SIH Industrial Fire Detection — Pending Tasks Before Team Handoff

## Current Status

**Git/GitHub setup is complete.**

- Local Git repository initialized on `main`
- First commit created: `f71fe1e`
- GitHub repository connected and pushed
- Working tree clean
- Raw FIRMS data, caches, checkpoints, and credentials are excluded
- Production model is committed
- Full test suite: **127 passed, 0 failed**

The machine-learning (ML) model is trained and packaged. Remaining work is mainly **production inference, integration, documentation, and teammate handoff**.

---

# Pending Tasks

## 1. Phase 5A — Run Final Inference on All 633 Events
**Priority: HIGH**

Apply the finalized production Random Forest (RF) model to all 633 events.

### Deliverables
- Prediction for every event
- Three-class prediction:
  - Industrial Thermal Activity
  - Agricultural Burning
  - Natural/Wildfire/Other
- Class probabilities
- Confidence level
- Event identifiers and coordinates preserved
- Row-count and uniqueness checks

### Rules
- **Do not retrain the model**
- **Do not change model parameters**
- Use the committed production model
- Sentinel-2 credentials are not required for inference because the production model uses 36 baseline features

---

## 2. Validate the 633-Event Prediction Output
**Priority: HIGH**

Audit the generated prediction dataset.

### Checks
- Exactly 633 events
- Exactly one prediction per event
- No duplicate `event_id`
- No missing prediction class
- Valid class probabilities
- Valid confidence values
- Source identifiers and coordinates unchanged
- Model/feature version recorded
- No synthetic values

### Deliverables
- Final prediction CSV
- Inference report
- Integrity summary

---

## 3. Prepare the Dashboard Data Package
**Priority: HIGH**

Create a clean dataset that frontend/backend teammates can consume without understanding the full research pipeline.

### Include
- Event ID
- Latitude/longitude
- FIRMS thermal information
- ML predicted class
- Class probabilities
- Confidence
- Relevant OpenStreetMap (OSM) context
- WorldCover land-cover information
- Sentinel-2 evidence/status where available
- Human-validation information where appropriate

### Scientific distinction

The dashboard should retain the project's **six-class evidence taxonomy** for validated/human-reviewed events, while the production ML model predicts the **three higher-level classes**.

Do not present model probability as ground truth.

---

## 4. Define the ML Backend/API Contract
**Priority: HIGH**

Create a simple interface for the frontend/plugin team.

### Minimum input
One event's 36 baseline features.

### Minimum output
- `event_id`
- `predicted_class`
- class probabilities
- confidence

The existing `src/models/predict.py` should remain the central inference interface.

### Goal

Frontend developers should not need to understand the Random Forest training or preprocessing internals.

---

## 5. Create a Reproducible Inference Command
**Priority: MEDIUM-HIGH**

Provide one simple command/script that teammates can use to reproduce predictions.

Example concept:

```text
python run_inference.py --input <events.csv> --output <predictions.csv>
```

The exact command should be finalized after Phase 5A.

Requirements:
- Uses the committed production model
- Validates required features
- Produces deterministic predictions
- Gives clear errors for missing features
- Does not require Sentinel-2 credentials

---

## 6. Improve the Project README for Teammates
**Priority: MEDIUM**

Document:
1. Project purpose and SIH problem statement
2. System architecture
3. Data sources
4. ML model
5. Three-class prediction target
6. Installation
7. Inference instructions
8. Model location
9. Data intentionally excluded from Git
10. Frontend/backend integration instructions

Keep detailed research reports separate from the main README.

---

## 7. Frontend/GIS Handoff
**Priority: HIGH once the prediction package is ready**

Give the frontend/plugin team:
- Final prediction dataset/schema
- ML prediction interface
- Field definitions
- Class definitions
- Confidence interpretation
- Evidence fields
- Example prediction record
- Uncertainty-display guidance

The dashboard should support:
- Thermal detections on a map
- Classification filters
- Event selection
- Evidence panel
- FIRMS details
- OSM context
- Land-cover context
- Sentinel-2 evidence/status
- ML prediction and probability
- Human-validation status where available

---

## 8. Final End-to-End Integration Test
**Priority: HIGH**

Verify:

```text
FIRMS Event
    ↓
Feature Record
    ↓
Production Model
    ↓
Prediction
    ↓
Backend/API
    ↓
Dashboard
    ↓
Map + Evidence + Classification
```

Test:
- Industrial Thermal Activity
- Agricultural Burning
- Natural/Wildfire/Other
- Missing Sentinel-2 evidence
- Missing OSM coverage
- Invalid/incomplete input
- High-probability prediction
- Uncertain prediction

---

# Completed Work — Do Not Repeat

### Data & Features
- FIRMS real-data ingestion
- VIIRS processing
- WorldCover integration
- OSM retrieval and spatial context
- Spatial, temporal, and thermal feature engineering
- WGS84/Haversine spatial-distance correction

### Ground Truth
- Human validation batch
- 100 reviewed events
- 76 usable ML labels
- 24 REVIEW_REQUIRED events held out
- Independent human-labeling workflow

### Sentinel-2
- Real Copernicus Data Space Ecosystem (CDSE) authentication
- Real Level-2A acquisition
- Spectral feature extraction
- Pre/post change features
- 633-event processing
- OAuth token-refresh recovery
- Recovery audit

### Machine Learning
- Three-class target finalized
- Baseline and Sentinel-2 model comparison
- Production Random Forest selected
- 5-fold cross-validation
- Out-of-fold evaluation
- Production model packaged
- Inference interface implemented
- Inference tests completed

### Git
- Git initialized
- Safe staging completed
- First commit created
- GitHub repository created
- Repository pushed
- Secrets/raw data/caches excluded

---

# Recommended Execution Order

```text
1. Full 633-event inference
          ↓
2. Prediction dataset validation
          ↓
3. Dashboard data package
          ↓
4. ML backend/API contract
          ↓
5. Reproducible inference command
          ↓
6. README/team documentation
          ↓
7. Frontend/GIS integration
          ↓
8. End-to-end testing
          ↓
9. SIH demo readiness
```

## Critical Rule

**Do not retrain or modify the production ML model unless a separate evidence-based model revision is deliberately approved.**

The objective now is to **productize and hand off the completed ML system**, not reopen model development.
