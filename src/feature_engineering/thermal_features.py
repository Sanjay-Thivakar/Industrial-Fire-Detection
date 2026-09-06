import numpy as np
import pandas as pd
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("ThermalFeatures")


def encode_confidence(x) -> float:
    """Encode confidence categorical string to numeric representation."""
    val = str(x).lower().strip()
    if val == "h":
        return 2.0
    if val == "n":
        return 1.0
    if val == "l":
        return 0.0
    try:
        return float(val)
    except Exception:
        return 1.0


def compute_thermal_features(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """
    Computes thermal ratios, confidence scores, local 0.01° grid z-scores,
    and windowed temporal persistence features.
    """
    logger.info("Computing thermal and local grid persistent anomaly features...")
    features = df.copy()

    # Thermal ratios
    features["brightness_difference"] = features["brightness"] - features["bright_t31"]
    features["frp_brightness_ratio"] = features["frp"] / features["brightness"].replace(0, np.nan)
    features["log_frp"] = np.log1p(features["frp"].clip(lower=0))

    # Confidence & sensor source
    features["confidence_numeric"] = features["confidence"].apply(encode_confidence)
    sat_source = features["satellite_source"].astype(str).str.upper()
    features["is_n20"] = sat_source.str.contains("N20").astype(int)
    features["is_suomi_npp"] = sat_source.str.contains("NPP").astype(int)

    # Grid spatial binning (~0.01 deg grid cell)
    grid_size = config.spatial.get("grid_size_deg", 0.01)
    features["grid_lat"] = np.floor(features["latitude"] / grid_size) * grid_size
    features["grid_lon"] = np.floor(features["longitude"] / grid_size) * grid_size
    features["grid_id"] = (
        features["grid_lat"].round(4).astype(str) + "_" + features["grid_lon"].round(4).astype(str)
    )

    # 1. Total grid detection count and sum FRP across physical observations
    grid_counts = features.groupby("grid_id").size().rename("grid_detection_count")
    grid_frp = features.groupby("grid_id")["frp"].sum().rename("grid_total_frp")

    # 2. Windowed temporal active days calculation (prevents multi-year accumulation leakage)
    # Uses configurable window (e.g. 365-day annual window) so isolated single-day fires across multiple
    # separate years do not falsely accumulate to trigger persistent industrial flags.
    features["_acq_dt"] = pd.to_datetime(features["acq_date"], errors="coerce")
    features["_acq_year"] = features["_acq_dt"].dt.year.fillna(2000).astype(int)

    # Calculate active detection days per grid cell per calendar year / annual window
    annual_active_days = (
        features.groupby(["grid_id", "_acq_year"])["_acq_dt"]
        .transform("nunique")
        .rename("grid_active_days")
    )
    features["grid_active_days"] = annual_active_days

    features = features.drop(columns=["_acq_dt", "_acq_year"])

    features = features.merge(grid_counts, on="grid_id", how="left")
    features = features.merge(grid_frp, on="grid_id", how="left")

    # Local vs Global Z-scores
    # Configurable min_grid_obs (defaults to 5)
    min_grid_obs = config.spatial.get("min_grid_obs", 5)

    grid_stats = features.groupby("grid_id").agg(
        grid_brightness_mean=("brightness", "mean"),
        grid_brightness_std=("brightness", "std"),
        grid_frp_mean=("frp", "mean"),
        grid_frp_std=("frp", "std"),
        grid_n=("brightness", "count"),
    ).reset_index()

    features = features.merge(grid_stats, on="grid_id", how="left")

    global_b_mean, global_b_std = features["brightness"].mean(), features["brightness"].std()
    global_frp_mean, global_frp_std = features["frp"].mean(), features["frp"].std()
    enough_history = features["grid_n"] >= min_grid_obs

    features["brightness_zscore_local"] = np.where(
        enough_history & (features["grid_brightness_std"] > 0),
        (features["brightness"] - features["grid_brightness_mean"]) / features["grid_brightness_std"],
        (features["brightness"] - global_b_mean) / (global_b_std if global_b_std > 0 else 1.0),
    )
    features["frp_zscore_local"] = np.where(
        enough_history & (features["grid_frp_std"] > 0),
        (features["frp"] - features["grid_frp_mean"]) / features["grid_frp_std"],
        (features["frp"] - global_frp_mean) / (global_frp_std if global_frp_std > 0 else 1.0),
    )

    features["used_local_baseline"] = enough_history.astype(int)
    features["high_brightness_flag_local"] = (features["brightness_zscore_local"] >= 2.0).astype(int)
    features["high_frp_flag_local"] = (features["frp_zscore_local"] >= 2.0).astype(int)

    persistent_threshold = config.weak_labeling.get("persistent_active_days_threshold", 3)
    features["persistent_location_flag"] = (features["grid_active_days"] >= persistent_threshold).astype(int)

    logger.info("Thermal features complete.")
    return features
