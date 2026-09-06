import pandas as pd
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("WeakLabeler")


def assign_weak_label_row(
    row: pd.Series,
    dist_threshold: float = 2000.0,
    persistent_threshold: int = 3
) -> str:
    """Assign weak heuristic label to a single record."""
    dist = row.get("distance_to_facility_m")
    near_facility = (dist is not None) and (dist <= dist_threshold)
    persistent = row.get("grid_active_days", 0) >= persistent_threshold
    local_spike = (row.get("high_brightness_flag_local", 0) == 1) or (row.get("high_frp_flag_local", 0) == 1)

    lc_class = str(row.get("landcover_class", "Unknown"))
    has_landcover = lc_class != "Unknown"
    built_up = lc_class == "Built-up"
    forest = lc_class == "Tree cover"
    cropland = lc_class == "Cropland"

    is_forest_season = row.get("is_forest_fire_season", 0) == 1
    is_stubble_season = row.get("is_stubble_burning_season", 0) == 1

    if has_landcover:
        if near_facility and built_up and persistent and not local_spike:
            return "Persistent Thermal Source"
        if near_facility and built_up and local_spike:
            return "Industrial Fire"
        if forest and not near_facility and is_forest_season:
            return "Forest Fire"
        if cropland and not persistent and is_stubble_season:
            return "Agricultural Burning"
        return "Other/Unclassified"
    else:
        # Fallback rules when landcover is unavailable
        if near_facility and persistent and not local_spike:
            return "Persistent Thermal Source"
        if near_facility and local_spike:
            return "Industrial Fire"
        if not near_facility and local_spike and is_forest_season:
            return "Possible Forest Fire"
        if not near_facility and not persistent and is_stubble_season:
            return "Possible Agricultural Burning"
        return "Other/Unclassified"


def generate_weak_labels(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """Generates weak heuristic labels for training the baseline Random Forest classifier."""
    logger.info("Generating weak labels for baseline classification...")
    features = df.copy()

    dist_thresh = config.weak_labeling.get("facility_distance_threshold_m", 2000.0)
    pers_thresh = config.weak_labeling.get("persistent_active_days_threshold", 3)

    features["weak_label"] = features.apply(
        lambda r: assign_weak_label_row(r, dist_thresh, pers_thresh), axis=1
    )

    label_counts = features["weak_label"].value_counts()
    logger.info("Weak label distribution:")
    logger.info(label_counts.to_dict())

    if features["weak_label"].nunique() < 2:
        logger.warning("Only 1 class found in weak labels. Model training requires at least 2 classes.")

    return features
