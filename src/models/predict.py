"""Inference module for the production 3-class thermal anomaly classifier.

Selected Model: Baseline Random Forest Classifier
Target Classes:
1. Industrial Thermal Activity
2. Agricultural Burning
3. Natural / Wildfire / Other

Required Input Features: Exactly the 36 baseline features derived from NASA FIRMS,
OpenStreetMap industrial facilities, and ESA WorldCover landcover.
(Sentinel-2 optical rasters are NOT required for production inference).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

logger = logging.getLogger("ThermalAnomalyInference")

# Default model location
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "outputs"
    / "phase_4d_models"
    / "final_model.joblib"
)

# Canonical 36 baseline features required by the production model
REQUIRED_FEATURES: List[str] = [
    # NASA FIRMS Thermal Intensity (8)
    "frp",
    "brightness",
    "bright_t31",
    "brightness_difference",
    "frp_brightness_ratio",
    "log_frp",
    "confidence_numeric",
    "is_day",
    # NASA FIRMS Temporal Persistence & Local Anomaly (10)
    "grid_detection_count",
    "grid_active_days",
    "persistent_location_flag",
    "grid_total_frp",
    "grid_brightness_mean",
    "high_brightness_flag_local",
    "high_frp_flag_local",
    "brightness_zscore_local",
    "frp_zscore_local",
    "is_stubble_burning_season",
    # ESA WorldCover Land Cover (1)
    "landcover_code",
    # OpenStreetMap Industrial Proximity & Hierarchy Context (17)
    "distance_to_facility_m",
    "nearest_facility_type",
    "nearest_facility_category",
    "nearest_facility_tier",
    "near_industrial_500m",
    "near_industrial_1000m",
    "near_industrial_2000m",
    "near_industrial_5000m",
    "near_industrial_10000m",
    "distance_to_higher_relevance_m",
    "nearest_hr_category",
    "near_higher_relevance_500m",
    "near_higher_relevance_1000m",
    "near_higher_relevance_2000m",
    "near_higher_relevance_5000m",
    "near_higher_relevance_10000m",
    "osm_coverage_status",
]

# Fields that represent ground truth or historical heuristics (target leakage guard)
TARGET_LEAKAGE_FIELDS: set = {
    "ml_target_3class",
    "human_ground_truth_class",
    "human_raw_label",
    "weak_label",
    "ground_truth_status",
    "human_validation_status",
    "human_industry_observation",
    "human_review_confidence",
    "is_unambiguous_ground_truth",
}

# Three official production target classes
PRODUCTION_CLASSES: List[str] = [
    "Agricultural Burning",
    "Industrial Thermal Activity",
    "Natural / Wildfire / Other",
]

# Confidence categorical tiers
CONFIDENCE_TIERS: List[str] = ["HIGH", "MEDIUM", "LOW"]

# Module-level model cache
_CACHED_MODEL: Optional[Pipeline] = None
_CACHED_MODEL_PATH: Optional[Path] = None


def get_required_features() -> List[str]:
    """Return the ordered list of 36 feature names required for inference."""
    return list(REQUIRED_FEATURES)


def load_production_model(model_path: Optional[Union[str, Path]] = None) -> Pipeline:
    """Load the trained production Pipeline (with ColumnTransformer and Classifier).

    Caches the model in memory to avoid repeated disk reads.
    """
    global _CACHED_MODEL, _CACHED_MODEL_PATH

    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH

    if _CACHED_MODEL is not None and _CACHED_MODEL_PATH == path:
        return _CACHED_MODEL

    if not path.exists():
        # Fallback to packaged location in phase_5_ml_handoff if primary path not found
        fallback_path = (
            Path(__file__).resolve().parent.parent.parent
            / "outputs"
            / "phase_5_ml_handoff"
            / "final_model.joblib"
        )
        if fallback_path.exists():
            path = fallback_path
        else:
            raise FileNotFoundError(
                f"Production model artifact not found at: {path} (or fallback: {fallback_path})"
            )

    logger.info("Loading production model from: %s", path)
    model = joblib.load(path)

    if not isinstance(model, Pipeline):
        raise TypeError(f"Expected scikit-learn Pipeline object, got: {type(model)}")

    _CACHED_MODEL = model
    _CACHED_MODEL_PATH = path
    return model


def determine_confidence_category(max_probability: float) -> str:
    """Determine probability-derived confidence category.

    Categories:
    - HIGH: max_probability >= 0.75
    - MEDIUM: 0.50 <= max_probability < 0.75
    - LOW: max_probability < 0.50
    """
    if max_probability >= 0.75:
        return "HIGH"
    elif max_probability >= 0.50:
        return "MEDIUM"
    else:
        return "LOW"


def validate_and_prepare_features(
    features: Union[Dict[str, Any], pd.Series, pd.DataFrame]
) -> pd.DataFrame:
    """Validate input features against production schema and guard against leakage.

    Returns:
        pd.DataFrame containing strictly the 36 required features.
    """
    # 1. Convert input to DataFrame
    if isinstance(features, dict):
        df_input = pd.DataFrame([features])
    elif isinstance(features, pd.Series):
        df_input = pd.DataFrame([features.to_dict()])
    elif isinstance(features, pd.DataFrame):
        df_input = features.copy()
    else:
        raise TypeError(
            f"Input features must be a dict, pd.Series, or pd.DataFrame, got: {type(features)}"
        )

    # 2. Check for target leakage
    present_leakage = [col for col in TARGET_LEAKAGE_FIELDS if col in df_input.columns]
    if present_leakage:
        raise ValueError(
            f"Target leakage detected! The following ground-truth/heuristic fields must NOT "
            f"be passed as inference features: {present_leakage}"
        )

    # 3. Check for missing required features
    missing_features = [col for col in REQUIRED_FEATURES if col not in df_input.columns]
    if missing_features:
        raise ValueError(
            f"Missing {len(missing_features)} required feature(s) for production model: {missing_features}. "
            f"Total expected features: {len(REQUIRED_FEATURES)}."
        )

    # 4. Return ordered subset of strictly required features
    return df_input[REQUIRED_FEATURES].copy()


def predict_event(
    features: Union[Dict[str, Any], pd.Series, pd.DataFrame],
    model_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Generate 3-class prediction and class probabilities for a single thermal event.

    Args:
        features: Dictionary, Series, or 1-row DataFrame containing the 36 baseline features.
        model_path: Optional custom path to final_model.joblib.

    Returns:
        Structured prediction result dictionary:
        {
            "prediction": str,
            "probabilities": {
                "Industrial Thermal Activity": float,
                "Agricultural Burning": float,
                "Natural / Wildfire / Other": float
            },
            "max_probability": float,
            "confidence": "HIGH" | "MEDIUM" | "LOW",
            "model_architecture": "Random Forest (Baseline)",
            "note": "Confidence reflects model prediction probability, not ground truth."
        }
    """
    prepared_df = validate_and_prepare_features(features)
    if len(prepared_df) != 1:
        raise ValueError(
            f"predict_event expects exactly 1 event record, received {len(prepared_df)} rows. "
            f"For batch prediction, use predict_batch()."
        )

    model = load_production_model(model_path)

    # Generate probabilities and class prediction
    proba_array = model.predict_proba(prepared_df)[0]
    classes = model.classes_

    prob_dict = {
        cls_name: round(float(proba), 4)
        for cls_name, proba in zip(classes, proba_array)
    }

    predicted_class = str(model.predict(prepared_df)[0])
    max_prob = round(float(np.max(proba_array)), 4)
    confidence_cat = determine_confidence_category(max_prob)

    return {
        "prediction": predicted_class,
        "probabilities": prob_dict,
        "max_probability": max_prob,
        "confidence": confidence_cat,
        "confidence_scale": {
            "HIGH": ">= 0.75",
            "MEDIUM": "0.50 - 0.74",
            "LOW": "< 0.50",
        },
        "model_architecture": "Random Forest Classifier (Baseline FIRMS+OSM+WorldCover)",
        "note": "Model confidence is derived strictly from class prediction probability. It is an algorithmic estimate, not ground truth.",
    }


def predict_batch(
    events_df: pd.DataFrame,
    model_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Generate predictions for multiple events in a batch."""
    prepared_df = validate_and_prepare_features(events_df)
    model = load_production_model(model_path)

    proba_matrix = model.predict_proba(prepared_df)
    preds = model.predict(prepared_df)
    classes = model.classes_

    results = []
    for i in range(len(prepared_df)):
        proba_row = proba_matrix[i]
        prob_dict = {
            cls_name: round(float(p), 4)
            for cls_name, p in zip(classes, proba_row)
        }
        max_p = round(float(np.max(proba_row)), 4)
        results.append({
            "prediction": str(preds[i]),
            "probabilities": prob_dict,
            "max_probability": max_p,
            "confidence": determine_confidence_category(max_p),
        })
    return results
