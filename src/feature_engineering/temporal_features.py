import pandas as pd
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("TemporalFeatures")


def compute_temporal_features(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """Computes temporal, diurnal, and seasonal features from acquisition date and time."""
    logger.info("Computing temporal and seasonal features...")
    features = df.copy()

    features["acq_date"] = pd.to_datetime(features["acq_date"], errors="coerce")
    features["day_of_year"] = features["acq_date"].dt.dayofyear
    features["month"] = features["acq_date"].dt.month
    features["year"] = features["acq_date"].dt.year

    acq_time_numeric = pd.to_numeric(features["acq_time"], errors="coerce").fillna(0)
    features["hour"] = (acq_time_numeric // 100).astype(int)

    if "daynight" in features.columns:
        features["is_day"] = features["daynight"].astype(str).str.upper().eq("D").astype(int)
    else:
        features["is_day"] = 0

    forest_months = config.weak_labeling.get("forest_fire_months", [2, 3, 4, 5])
    stubble_months = config.weak_labeling.get("stubble_burning_months", [4, 5, 10, 11])

    features["is_forest_fire_season"] = features["month"].isin(forest_months).astype(int)
    features["is_stubble_burning_season"] = features["month"].isin(stubble_months).astype(int)

    logger.info("Temporal features complete.")
    return features
