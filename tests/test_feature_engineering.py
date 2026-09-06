import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from src.config import Config
from src.feature_engineering.thermal_features import compute_thermal_features, encode_confidence
from src.feature_engineering.temporal_features import compute_temporal_features
from src.feature_engineering.spatial_features import compute_spatial_features


def test_confidence_encoding():
    assert encode_confidence("h") == 2.0
    assert encode_confidence("n") == 1.0
    assert encode_confidence("l") == 0.0
    assert encode_confidence("85") == 85.0
    assert encode_confidence("invalid") == 1.0


def test_thermal_features_calculation():
    config = Config.load()
    df = pd.DataFrame({
        "latitude": [11.0, 11.0, 11.0, 11.0, 11.0, 11.0],
        "longitude": [78.0, 78.0, 78.0, 78.0, 78.0, 78.0],
        "brightness": [320.0, 310.0, 315.0, 305.0, 308.0, 380.0],
        "bright_t31": [290.0, 290.0, 290.0, 290.0, 290.0, 290.0],
        "frp": [10.0, 5.0, 8.0, 4.0, 6.0, 50.0],
        "confidence": ["h", "n", "l", "90", "n", "h"],
        "satellite_source": ["VIIRS_N20"] * 6,
        "acq_date": ["2023-03-01"] * 6,
        "acq_time": [1200] * 6,
    })

    res = compute_thermal_features(df, config)

    assert "brightness_difference" in res.columns
    assert res["brightness_difference"].iloc[0] == 30.0
    assert "frp_brightness_ratio" in res.columns
    assert res["frp_brightness_ratio"].iloc[0] == pytest.approx(10.0 / 320.0)
    assert "log_frp" in res.columns
    assert res["log_frp"].iloc[0] == pytest.approx(np.log1p(10.0))

    # Grid statistics check
    assert res["grid_detection_count"].iloc[0] == 6
    assert res["used_local_baseline"].iloc[0] == 1  # 6 obs >= min_grid_obs 5
    assert res["high_brightness_flag_local"].iloc[5] == 1  # 380 K is a local spike vs mean ~323 K


def test_temporal_grid_active_days_multiyear():
    # Verify that multi-year data counts grid_active_days per annual window (preventing multi-year false positive accumulation)
    config = Config.load()

    # Site active 1 day in 2020, 1 day in 2022, 1 day in 2024 (3 total days over 5 years, but only 1 day in each year)
    df = pd.DataFrame({
        "latitude": [11.0, 11.0, 11.0],
        "longitude": [78.0, 78.0, 78.0],
        "brightness": [320.0, 320.0, 320.0],
        "bright_t31": [290.0, 290.0, 290.0],
        "frp": [10.0, 10.0, 10.0],
        "confidence": ["h", "h", "h"],
        "satellite_source": ["VIIRS_N20"] * 3,
        "acq_date": ["2020-03-01", "2022-03-01", "2024-03-01"],
        "acq_time": [1200] * 3,
    })

    res = compute_thermal_features(df, config)
    # Active days in each year should be 1 (NOT accumulated to 3 across 5 years)
    assert res["grid_active_days"].iloc[0] == 1
    assert res["grid_active_days"].iloc[1] == 1
    assert res["grid_active_days"].iloc[2] == 1
    assert res["persistent_location_flag"].iloc[0] == 0


def test_configurable_min_grid_obs():
    # Test that min_grid_obs loaded from config dictates whether local baseline is used
    config_dict = {
        "spatial": {
            "grid_size_deg": 0.01,
            "min_grid_obs": 10  # Require 10 obs for local baseline
        },
        "weak_labeling": {"persistent_active_days_threshold": 3}
    }
    config = Config(config_dict, project_root=Path("."))

    # 6 obs (less than min_grid_obs 10)
    df = pd.DataFrame({
        "latitude": [11.0] * 6,
        "longitude": [78.0] * 6,
        "brightness": [320.0] * 6,
        "bright_t31": [290.0] * 6,
        "frp": [10.0] * 6,
        "confidence": ["h"] * 6,
        "satellite_source": ["VIIRS_N20"] * 6,
        "acq_date": ["2023-03-01"] * 6,
        "acq_time": [1200] * 6,
    })

    res = compute_thermal_features(df, config)
    # Should fall back to global baseline since 6 < min_grid_obs 10
    assert res["used_local_baseline"].iloc[0] == 0


def test_spatial_features_planar_distance():
    config = Config.load()
    fires_df = pd.DataFrame({
        "latitude": [11.0],
        "longitude": [78.0],
        "brightness": [320.0],
        "frp": [10.0]
    })
    # Phase 2C schema: normalized_category and relevance_tier are required
    osm_df = pd.DataFrame({
        "osm_id": [101],
        "osm_type": ["node"],
        "latitude": [11.0],  # Exactly coincident
        "longitude": [78.0],
        "name": ["Test Facility"],
        "operator": ["Test Op"],
        "facility_type": ["Power Plant"],
        "normalized_category": ["Power Plant"],
        "relevance_tier": ["HIGHER_RELEVANCE"],
    })

    res = compute_spatial_features(fires_df, osm_df, config)
    assert res["distance_to_facility_m"].iloc[0] == pytest.approx(0.0, abs=1e-3)
    assert res["near_industrial_500m"].iloc[0] == 1
    assert res["facility_type_code"].iloc[0] == 1
    # Phase 2C: HIGHER_RELEVANCE distance should also be zero for a coincident facility
    assert res["distance_to_higher_relevance_m"].iloc[0] == pytest.approx(0.0, abs=1e-3)
    assert res["near_higher_relevance_500m"].iloc[0] == 1
