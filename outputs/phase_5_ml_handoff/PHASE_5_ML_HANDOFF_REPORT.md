# Phase 5 Final ML Engineering Handoff Report

## Executive Summary
This report formalizes the final machine learning handoff for the 3-Class Thermal Anomaly Classification system. Phase 4D model training and cross-validation are complete and accepted. In this handoff phase, the production model was packaged into a self-contained, reproducible inference interface with automated validation, robust probability estimation, explicit confidence categorization, comprehensive documentation, and automated test coverage.

All 127 automated project tests are passing without regressions. No models were retrained, no architectures were altered, no additional data was collected, and no target leakage occurs.

---

## 1. Selected Production Model
- **Algorithm:** Random Forest Classifier (`sklearn.ensemble.RandomForestClassifier`) wrapped in a self-contained `sklearn.pipeline.Pipeline` with `ColumnTransformer` (median numeric imputation + OneHotEncoder for categoricals).
- **Target Variable:** `ml_target_3class`
- **Output Classes (3):**
  1. `Industrial Thermal Activity`
  2. `Agricultural Burning`
  3. `Natural / Wildfire / Other`
- **Model Parameters:** `n_estimators=100`, `max_depth=6`, `min_samples_split=4`, `class_weight='balanced'`, `random_state=42`.
- **Training Population:** 76 human-validated ground-truth records from Tamil Nadu FIRMS active fire events (15 Industrial, 50 Agricultural, 11 Natural/Wildfire/Other).
- **Packaging Location:** `outputs/phase_5_ml_handoff/final_model.joblib` (referenced also at `outputs/phase_4d_models/final_model.joblib`).
- **File Size:** ~236 KB.

---

## 2. Model Performance Summary
Evaluated strictly via 5-Fold Stratified Cross-Validation on the 76 clean human-validated samples:

| Metric | Out-of-Fold (OOF) Score | 5-Fold CV Mean ± Std |
| :--- | :--- | :--- |
| **Macro F1 Score** | **0.7772** | **0.7594 ± 0.1173** |
| **Balanced Accuracy** | **0.7693** | — |
| **Overall Accuracy** | **85.53%** (65 / 76) | — |
| **Industrial Thermal Activity Recall** | **93.33%** (14 / 15) | — |
| **Industrial Thermal Activity Precision**| **87.50%** (14 / 16) | — |
| **Industrial Thermal Activity F1** | **0.9032** | — |
| **Agricultural Burning Recall** | **90.00%** (45 / 50) | — |
| **Agricultural Burning Precision**| **93.75%** (45 / 48) | — |
| **Agricultural Burning F1** | **0.9184** | — |
| **Natural / Wildfire / Other Recall** | **54.55%** (6 / 11) | — |
| **Natural / Wildfire / Other Precision** | **50.00%** (6 / 12) | — |
| **Natural / Wildfire / Other F1** | **0.5217** | — |

---

## 3. Inference Interface & Public API
Module: `src/models/predict.py`

### Public Functions
- `predict_event(features: dict | pd.Series | pd.DataFrame, model_path: Optional[str] = None) -> dict`: Single event inference returning class prediction, normalized probabilities, max probability, and confidence tier.
- `predict_batch(events_df: pd.DataFrame, model_path: Optional[str] = None) -> list[dict]`: Batch inference over a tabular dataset.
- `load_production_model(model_path: Optional[str] = None) -> Pipeline`: Cached pipeline loader.
- `get_required_features() -> list[str]`: Ordered list of the 36 required baseline features.

### Structured Output Format
```json
{
  "prediction": "Industrial Thermal Activity",
  "probabilities": {
    "Agricultural Burning": 0.0513,
    "Industrial Thermal Activity": 0.9184,
    "Natural / Wildfire / Other": 0.0303
  },
  "max_probability": 0.9184,
  "confidence": "HIGH",
  "confidence_scale": {
    "HIGH": ">= 0.75",
    "MEDIUM": "0.50 - 0.74",
    "LOW": "< 0.50"
  },
  "model_architecture": "Random Forest Classifier (Baseline FIRMS+OSM+WorldCover)",
  "note": "Model confidence is derived strictly from class prediction probability. It is an algorithmic estimate, not ground truth."
}
```

---

## 4. Required Features & Validation
The production model strictly requires the **36 Baseline Features** documented in `outputs/phase_5_ml_handoff/feature_manifest_baseline.csv`:
- **NASA FIRMS Thermal Intensity (8):** `frp`, `brightness`, `bright_t31`, `brightness_difference`, `frp_brightness_ratio`, `log_frp`, `confidence_numeric`, `is_day`.
- **NASA FIRMS Persistence & Anomaly (10):** `grid_detection_count`, `grid_active_days`, `persistent_location_flag`, `grid_total_frp`, `grid_brightness_mean`, `high_brightness_flag_local`, `high_frp_flag_local`, `brightness_zscore_local`, `frp_zscore_local`, `is_stubble_burning_season`.
- **ESA WorldCover (1):** `landcover_code`.
- **OpenStreetMap Spatial Proximity & Context (17):** `distance_to_facility_m`, `nearest_facility_type`, `nearest_facility_category`, `nearest_facility_tier`, `near_industrial_500m`, `near_industrial_1000m`, `near_industrial_2000m`, `near_industrial_5000m`, `near_industrial_10000m`, `distance_to_higher_relevance_m`, `nearest_hr_category`, `near_higher_relevance_500m`, `near_higher_relevance_1000m`, `near_higher_relevance_2000m`, `near_higher_relevance_5000m`, `near_higher_relevance_10000m`, `osm_coverage_status`.

### Validation Behavior
- If any of the 36 required features are absent, `predict_event()` immediately raises a clear `ValueError` specifying the exact missing feature names.
- If any ground-truth or human review fields (`TARGET_LEAKAGE_FIELDS`) are provided, `predict_event()` raises a hard `ValueError` to prevent data leakage.
- **Sentinel-2 optical features are NOT required.** The frontend and plugin can run full inference using only satellite thermal data and GIS features without requiring Copernicus CDSE API tokens.

---

## 5. Confidence Categorization
Confidence is categorized into three unambiguous tiers based strictly on the model's highest predicted probability:
- **`HIGH`** ($\ge 0.75$): Strong ensemble agreement among decision trees.
- **`MEDIUM`** ($0.50 - 0.74$): Majority consensus with moderate variance.
- **`LOW`** ($< 0.50$): Ambiguous or evenly split class distribution.

### Distinction from Sensor & Human Confidence
- **Model Confidence:** Algorithmic probability of the Random Forest classifier.
- **NASA VIIRS Sensor Confidence:** Satellite instrument detection confidence (`low`, `nominal`, `high`).
- **Human Review Confidence:** Analyst verification certainty during visual ground-truth audit.

---

## 6. Packaged Artifact Locations (`outputs/phase_5_ml_handoff/`)
1. `final_model.joblib`: Serialized Scikit-Learn Pipeline (236 KB).
2. `final_model_metadata.json`: Model architecture, hyperparameter, and performance metadata.
3. `model_manifest.json`: Full specification of model inputs, outputs, CV scheme, and class mappings.
4. `feature_manifest_baseline.csv`: Schema and descriptions for all 36 required features.
5. `feature_importance.csv`: Baseline Random Forest Gini impurity feature importances.
6. `ML_INFERENCE_README.md`: Complete developer guide covering all 12 operational sections.
7. `inference_example.py`: Standalone runnable example demonstrating inference on a real event.
8. `PHASE_5_ML_HANDOFF_REPORT.md`: This comprehensive handoff document.

---

## 7. Verification & Automated Test Results
- **Inference Unit Tests (`tests/test_ml_inference.py`):** 6/6 tests passing (model loading, valid predictions, 3-class constraint, probability normalization, missing feature exceptions, target leakage guards, batch inference, reproducibility).
- **Full Project Test Suite:** **127 passed, 0 failed** across all test modules (`test_phase4d_models.py`, `test_phase4c_ml.py`, `test_sentinel2_*.py`, etc.).
- **Reproducibility Test:** Executed inference on real event `FIRMS_TN_0010` across consecutive independent executions. Output prediction (`Industrial Thermal Activity`), probabilities (`0.9184`, `0.0513`, `0.0303`), and confidence (`HIGH`) showed 100% bitwise identity.

---

## 8. Git Handoff & Version Control Recommendations
### Git Repository Status
The project directory currently has no active `.git` directory initialized (`fatal: not a git repository`).

### .gitignore Setup
A `.gitignore` file has been created in the workspace root. It excludes:
- Python bytecode caches (`__pycache__/`, `.pytest_cache/`, `*.pyc`).
- Virtual environments (`.venv/`, `venv/`).
- API credentials and secrets (`.env`, `secrets.json`, `config/secrets*.yaml`).
- High-volume raw satellite data files exceeding 50 MB (e.g., `data/raw/firms/*/*.csv`, which range up to 271 MB).
- Ephemeral tile caches (`data/cache/osm_tiles/`, `data/cache/ne_admin1/`).

### Files That SHOULD Be Committed
- **Source code:** `src/models/predict.py`, `src/feature_engineering/`, `src/osm_mining/`, `src/pipelines/`.
- **Test suite:** `tests/test_ml_inference.py`, `tests/test_phase4d_models.py`, `tests/test_phase4c_ml.py`, and all unit tests.
- **Packaged Model & Manifests:**
  - `outputs/phase_5_ml_handoff/final_model.joblib` (236 KB — well under GitHub's 100 MB limit; safe for standard Git commit without LFS).
  - `outputs/phase_5_ml_handoff/model_manifest.json`
  - `outputs/phase_5_ml_handoff/final_model_metadata.json`
  - `outputs/phase_5_ml_handoff/feature_manifest_baseline.csv`
  - `outputs/phase_5_ml_handoff/feature_importance.csv`
  - `outputs/phase_5_ml_handoff/ML_INFERENCE_README.md`
  - `outputs/phase_5_ml_handoff/inference_example.py`
  - `outputs/phase_5_ml_handoff/PHASE_5_ML_HANDOFF_REPORT.md`
- **Curation Datasets & Phase Reports:**
  - `outputs/phase_4c_ml/ml_3class_dataset.csv` (clean 76-record training dataset).
  - `outputs/phase_4b_ground_truth/` and `outputs/phase_4a_dataset_audit/` summary markdown reports.

### Files That Should NOT Be Committed
- `data/raw/firms/viirs_noaa20/fire_nrt_J1V-C2_565335.csv` (271.6 MB)
- `data/raw/firms/viirs_snpp/fire_nrt_SV-C2_565336.csv` (244.8 MB)
- `data/raw/firms/modis/fire_nrt_M-C61_565334.csv` (59.8 MB)
- `data/cache/ne_admin1.zip` (14.2 MB)

*(If the team desires to track large raw FIRMS CSVs in Git, Git LFS must be configured: `git lfs track "data/raw/firms/**/*.csv"`).*

---

## 9. Integration Guidance for Teammates (Frontend & Plugin)
1. **No External API Dependencies at Runtime:** The production classifier requires only spatial and thermal attributes. No Sentinel-2 Copernicus API tokens, downloads, or network calls are required for prediction.
2. **Simple Single-Function Call:** Pass the feature dictionary to `predict_event(features)`.
3. **Display Rules:**
   - Present `prediction` as the primary classification.
   - Present `confidence` (`HIGH` / `MEDIUM` / `LOW`) and `max_probability` in UI badges or tooltips.
   - Clarify in the UI that this is an **algorithmic probability**, not human ground truth.
   - Keep the detailed 6-class taxonomy for human-validated event cards and dashboard details, rather than treating it as a raw model output.
