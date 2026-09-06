# Production ML Model Inference & Integration Guide

## 1. What the Model Does
The production machine learning model is an automated thermal anomaly classifier trained to attribute satellite-detected hotspots (e.g., NASA VIIRS / FIRMS) to their physical and operational origin. 

Given a set of 36 geospatial, contextual, and temporal features (derived from FIRMS thermal observations, OpenStreetMap spatial infrastructure, and ESA WorldCover land cover), the classifier computes class posterior probabilities and predicts the most likely source of the thermal event.

---

## 2. The Three Output Classes
The supervised model classifies each thermal event into one of three official operational classes:
1. **`Industrial Thermal Activity`**: Continuous or episodic thermal signatures associated with manufacturing plants, steel mills, cement kilns, chemical refineries, flare stacks, or brick kilns.
2. **`Agricultural Burning`**: Ephemeral open-field crop residue burning, post-harvest clearing, or stubble burning, typically occurring in agricultural zones with seasonal clustering.
3. **`Natural / Wildfire / Other`**: Forest fires, scrubland blazes, brush fires, or unclassified non-industrial open burning events.

---

## 3. Required Input Features (36 Baseline Features)
The production classifier is based on the **Baseline Feature Set** and does **NOT** require optical Sentinel-2 imagery or API access at inference time.

The 36 required features are:
- **NASA FIRMS Thermal Intensity (8 features):**
  - `frp`: Fire Radiative Power (MW)
  - `brightness`: Brightness temperature in I4 channel (K)
  - `bright_t31`: Brightness temperature in I5 channel (K)
  - `brightness_difference`: Difference I4 - I5 (K), active combustion indicator
  - `frp_brightness_ratio`: Ratio of FRP to brightness temperature
  - `log_frp`: Log-transformed Fire Radiative Power (log1p)
  - `confidence_numeric`: Sensor detection confidence (1=nominal, 2=high)
  - `is_day`: Daytime detection indicator (1=day, 0=night)
- **NASA FIRMS Persistence & Anomaly (10 features):**
  - `grid_detection_count`: Total historical detections in 0.05 deg grid
  - `grid_active_days`: Active anomaly days in local 0.05 deg grid
  - `persistent_location_flag`: Indicator for grid_active_days >= 3
  - `grid_total_frp`: Cumulative FRP in local grid cell
  - `grid_brightness_mean`: Mean brightness temperature across grid detections
  - `high_brightness_flag_local`: Local spatial spike in brightness flag
  - `high_frp_flag_local`: Local spatial spike in FRP flag
  - `brightness_zscore_local`: Local standardized z-score of brightness
  - `frp_zscore_local`: Local standardized z-score of FRP
  - `is_stubble_burning_season`: Post-harvest crop burning season indicator
- **ESA WorldCover (1 feature):**
  - `landcover_code`: Discrete land cover classification code (e.g., 10=Tree cover, 20=Shrubland, 30=Grassland, 40=Cropland, 50=Built-up)
- **OpenStreetMap Spatial Proximity & Context (17 features):**
  - `distance_to_facility_m`: Geodesic distance to nearest industrial facility (m)
  - `nearest_facility_type`: Primary industrial facility classification type
  - `nearest_facility_category`: Specific industrial manufacturing/process sector
  - `nearest_facility_tier`: Relevance tier (HIGHER_RELEVANCE, CAUTION, GENERAL)
  - `near_industrial_500m`: Binary proximity indicator <= 500m
  - `near_industrial_1000m`: Binary proximity indicator <= 1000m
  - `near_industrial_2000m`: Binary proximity indicator <= 2000m
  - `near_industrial_5000m`: Binary proximity indicator <= 5000m
  - `near_industrial_10000m`: Binary proximity indicator <= 10000m
  - `distance_to_higher_relevance_m`: Distance to nearest high-relevance industrial facility (m)
  - `nearest_hr_category`: Category of nearest high-relevance facility
  - `near_higher_relevance_500m`: High-relevance proximity indicator <= 500m
  - `near_higher_relevance_1000m`: High-relevance proximity indicator <= 1000m
  - `near_higher_relevance_2000m`: High-relevance proximity indicator <= 2000m
  - `near_higher_relevance_5000m`: High-relevance proximity indicator <= 5000m
  - `near_higher_relevance_10000m`: High-relevance proximity indicator <= 10000m
  - `osm_coverage_status`: OSM Overpass retrieval status (COVERED/FAILED_TILE)

> **CRITICAL NOTE:** Ground-truth and review fields (e.g., `ml_target_3class`, `human_ground_truth_class`, `human_review_confidence`, `weak_label`) are strictly rejected by the validator to prevent data leakage.

---

## 4. How to Load the Model
The model is packaged as a standard self-contained Scikit-Learn Pipeline serialized via `joblib`:

```python
from src.models.predict import load_production_model

# Load using the default relative path (searches phase_5_ml_handoff, then phase_4d_models)
model = load_production_model()

# Or specify an explicit path:
model = load_production_model("outputs/phase_5_ml_handoff/final_model.joblib")
```

The loaded object is a `sklearn.pipeline.Pipeline` containing:
1. `prep`: A `ColumnTransformer` handling median imputation for numerical features and OneHotEncoding for categorical features.
2. `clf`: A balanced `RandomForestClassifier`.

---

## 5. How to Call `predict_event()`
The primary public interface is provided in `src/models/predict.py`:

```python
from src.models.predict import predict_event

# Single event inference
result = predict_event(event_features_dict)
```

For batch inference on a Pandas DataFrame:
```python
from src.models.predict import predict_batch

results_list = predict_batch(events_dataframe)
```

---

## 6. Example Input
```python
sample_input = {
    "frp": 2.09,
    "brightness": 325.4,
    "bright_t31": 298.1,
    "brightness_difference": 27.3,
    "frp_brightness_ratio": 0.0064,
    "log_frp": 1.128,
    "confidence_numeric": 2,
    "is_day": 1,
    "grid_detection_count": 12,
    "grid_active_days": 8,
    "persistent_location_flag": 1,
    "grid_total_frp": 38.5,
    "grid_brightness_mean": 320.1,
    "high_brightness_flag_local": 0,
    "high_frp_flag_local": 0,
    "brightness_zscore_local": 0.42,
    "frp_zscore_local": -0.15,
    "is_stubble_burning_season": 0,
    "landcover_code": 50,
    "distance_to_facility_m": 120.5,
    "nearest_facility_type": "industrial",
    "nearest_facility_category": "manufacturing",
    "nearest_facility_tier": "HIGHER_RELEVANCE",
    "near_industrial_500m": 1,
    "near_industrial_1000m": 1,
    "near_industrial_2000m": 1,
    "near_industrial_5000m": 1,
    "near_industrial_10000m": 1,
    "distance_to_higher_relevance_m": 120.5,
    "nearest_hr_category": "manufacturing",
    "near_higher_relevance_500m": 1,
    "near_higher_relevance_1000m": 1,
    "near_higher_relevance_2000m": 1,
    "near_higher_relevance_5000m": 1,
    "near_higher_relevance_10000m": 1,
    "osm_coverage_status": "COVERED"
}
```

---

## 7. Example Output
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

## 8. Meaning of Probabilities
- `probabilities`: Normalized posterior probabilities across all 3 classes generated by the Random Forest ensemble (the fraction of decision trees voting for each class).
- `max_probability`: The highest probability score among the 3 classes, corresponding to the `prediction`.
- The sum of probabilities always equals 1.0 (within standard floating point precision).

---

## 9. Meaning of Confidence
To prevent user confusion and operational misinterpretations, the system strictly separates three concepts of confidence:

1. **Model Confidence (`HIGH` / `MEDIUM` / `LOW`)**:
   - **Definition:** Derived strictly from the model's highest class probability:
     - `HIGH`: $\ge 0.75$ (strong ensemble consensus)
     - `MEDIUM`: $0.50 - 0.74$ (majority consensus, some disagreement)
     - `LOW`: $< 0.50$ (ambiguous or split distribution)
   - **Nature:** Algorithmic certainty. It is **NOT** ground truth.
2. **NASA VIIRS Sensor Confidence (`low`, `nominal`, `high`)**:
   - **Definition:** The radiometric quality score produced by the VIIRS active fire detection algorithm (FIRMS). Indicates whether the satellite detected an actual thermal anomaly versus sensor noise/sun glint.
3. **Human Review Confidence (`HIGH`, `MEDIUM`, `LOW`)**:
   - **Definition:** Analyst certainty recorded during manual validation using high-resolution optical imagery and spatial audits.

---

## 10. Model Performance
Evaluated on the independent human ground-truth dataset ($N=76$) via 5-Fold Stratified Cross-Validation:

| Metric | Out-of-Fold (OOF) Value | 5-Fold CV Mean ± Std |
| :--- | :--- | :--- |
| **Macro F1** | **0.7772** | **0.7594 ± 0.1173** |
| **Balanced Accuracy** | **0.7693** | — |
| **Overall Accuracy** | **85.53%** | — |
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

## 11. Important Limitations
1. **Natural / Wildfire / Other Sample Size:** With only 11 natural/wildfire ground-truth events in the training partition, the classifier has moderate sensitivity (Recall: 54.55%) for rare wild blazes.
2. **Cloud Cover & Optical Gaps:** The production model relies on satellite thermal detection (VIIRS) and land-use context. It does not inspect optical spectral reflectance changes.
3. **Boundary Contexts:** Hotspots located on the immediate boundary between an industrial complex and an agricultural parcel depend heavily on OSM mapping completeness.
4. **No Direct Sub-Class Distinction:** The model cannot differentiate between a coal-fired power plant and an oil refinery, as both fall under `Industrial Thermal Activity`.

---

## 12. Difference Between 3-Class ML Prediction & Six-Class Dashboard Taxonomy

| Feature / Aspect | Supervised 3-Class ML Prediction | Six-Class Characterization Taxonomy |
| :--- | :--- | :--- |
| **Classes** | 1. `Industrial Thermal Activity`<br>2. `Agricultural Burning`<br>3. `Natural / Wildfire / Other` | 1. `Industrial Fire`<br>2. `Persistent Industrial Thermal Source`<br>3. `Agricultural Burning`<br>4. `Natural/Forest Fire`<br>5. `Other/Unclassified`<br>6. `Unknown/Insufficient Evidence` |
| **Role in System** | **Automated Real-Time Inference** engine for incoming raw satellite events. | **Human-Validated Event Characterization** & detailed dashboard presentation. |
| **Generation** | Machine learning model (`RandomForestClassifier`). | Human visual audit / post-processing rules. |
| **Why Not 6 Classes in ML?**| Sparse ground-truth sample sizes in specific sub-classes (e.g., only 2 transient industrial fires vs 13 persistent sources) make 6-class supervised training statistically unviable. | Granular operational reporting required by municipal and environmental stakeholders. |
| **Integration Pattern**| Frontend should display the **3-class ML prediction & confidence** as the primary algorithmic label. | Detailed dashboard event views can supplement this with the 6-class validated category when available. |
