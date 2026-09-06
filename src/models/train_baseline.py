import numpy as np
import pandas as pd
from typing import Dict, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("BaselineModel")

MODEL_FEATURES = [
    "brightness", "bright_t31", "frp", "scan", "track",
    "brightness_difference", "frp_brightness_ratio", "log_frp",
    "confidence_numeric", "is_n20", "is_suomi_npp", "is_day", "hour",
    "month", "day_of_year",
    "distance_to_facility_km", "industrial_facility_present", "facility_type_code",
    "near_industrial_500m", "near_industrial_1000m", "near_industrial_2000m", "near_industrial_5000m",
    "grid_detection_count", "grid_active_days", "grid_total_frp",
    "brightness_zscore_local", "frp_zscore_local", "used_local_baseline",
    "is_forest_fire_season", "is_stubble_burning_season",
    "landcover_code",
]


def train_baseline_rf(
    df: pd.DataFrame, config: Config
) -> Tuple[RandomForestClassifier, pd.DataFrame, Dict[str, float]]:
    """
    Trains baseline Random Forest classifier on weak labels with leakage-free train/test split.
    Adds predicted_class and predicted_class_confidence to output DataFrame.
    """
    logger.info("Preparing feature matrix for baseline Random Forest training...")
    model_df = df.dropna(subset=["weak_label"]).copy()

    # Pre-coerce numeric types
    for col in MODEL_FEATURES:
        if col in model_df.columns:
            model_df[col] = pd.to_numeric(model_df[col], errors="coerce")
        else:
            logger.warning(f"Feature '{col}' missing from DataFrame. Filling with 0.")
            model_df[col] = 0.0

    X = model_df[MODEL_FEATURES].copy()
    y = model_df["weak_label"]

    if y.nunique() < 2:
        raise RuntimeError(
            f"Cannot train classifier: only 1 class ({y.unique()[0]}) present in weak labels."
        )

    # Train / Test split without data leakage
    test_size = config.model.get("test_size", 0.25)
    random_state = config.model.get("random_state", 42)
    
    min_class_count = y.value_counts().min()
    can_stratify = min_class_count >= 2

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y if can_stratify else None
    )

    # Impute missing values using train set median only (prevents data leakage)
    train_medians = X_train.median().fillna(0)
    X_train_imp = X_train.fillna(train_medians)
    X_test_imp = X_test.fillna(train_medians)

    logger.info(f"Training set: {len(X_train):,} rows | Test set: {len(X_test):,} rows")
    logger.info("Class distribution in training set:")
    logger.info(y_train.value_counts().to_dict())

    # Fit Random Forest Classifier
    clf = RandomForestClassifier(
        n_estimators=config.model.get("n_estimators", 300),
        max_depth=config.model.get("max_depth", 12),
        min_samples_leaf=config.model.get("min_samples_leaf", 3),
        class_weight=config.model.get("class_weight", "balanced"),
        random_state=random_state,
        n_jobs=config.model.get("n_jobs", -1),
    )
    clf.fit(X_train_imp, y_train)

    # Evaluate on test set
    y_pred = clf.predict(X_test_imp)
    report_str = classification_report(y_test, y_pred, zero_division=0)
    logger.info(f"\nHeld-out Test Classification Report:\n{report_str}")

    # Top feature importances
    importances = pd.Series(clf.feature_importances_, index=MODEL_FEATURES).sort_values(ascending=False)
    logger.info("\nTop 10 Feature Importances:")
    logger.info(importances.head(10).to_dict())

    # Generate predictions across full dataset
    full_df = df.copy()
    for col in MODEL_FEATURES:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors="coerce")
        else:
            full_df[col] = 0.0

    X_full = full_df[MODEL_FEATURES].fillna(train_medians)
    full_df["predicted_class"] = clf.predict(X_full)
    full_df["predicted_class_confidence"] = clf.predict_proba(X_full).max(axis=1)

    return clf, full_df, importances.to_dict()
