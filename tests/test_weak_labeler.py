import pandas as pd
import pytest
from src.labeling.weak_labeler import assign_weak_label_row


def test_weak_label_landcover_aware():
    # Case 1: Industrial Fire (near facility <= 2000m, Built-up, local spike)
    row1 = pd.Series({
        "distance_to_facility_m": 500.0,
        "grid_active_days": 1,
        "high_brightness_flag_local": 1,
        "high_frp_flag_local": 0,
        "landcover_class": "Built-up",
        "is_forest_fire_season": 0,
        "is_stubble_burning_season": 0,
    })
    assert assign_weak_label_row(row1) == "Industrial Fire"

    # Case 2: Persistent Thermal Source (near facility <= 2000m, Built-up, persistent >= 3 days, no spike)
    row2 = pd.Series({
        "distance_to_facility_m": 500.0,
        "grid_active_days": 5,
        "high_brightness_flag_local": 0,
        "high_frp_flag_local": 0,
        "landcover_class": "Built-up",
        "is_forest_fire_season": 0,
        "is_stubble_burning_season": 0,
    })
    assert assign_weak_label_row(row2) == "Persistent Thermal Source"

    # Case 3: Forest Fire (Tree cover, far from facility, forest season)
    row3 = pd.Series({
        "distance_to_facility_m": 10000.0,
        "grid_active_days": 1,
        "high_brightness_flag_local": 0,
        "high_frp_flag_local": 0,
        "landcover_class": "Tree cover",
        "is_forest_fire_season": 1,
        "is_stubble_burning_season": 0,
    })
    assert assign_weak_label_row(row3) == "Forest Fire"


def test_weak_label_fallback():
    # Case 4: Landcover missing ("Unknown"), near facility <= 2000m, local spike -> Industrial Fire
    row4 = pd.Series({
        "distance_to_facility_m": 1200.0,
        "grid_active_days": 1,
        "high_brightness_flag_local": 1,
        "high_frp_flag_local": 0,
        "landcover_class": "Unknown",
        "is_forest_fire_season": 0,
        "is_stubble_burning_season": 0,
    })
    assert assign_weak_label_row(row4) == "Industrial Fire"

    # Case 5: Landcover missing, far from facility, spike + forest season -> Possible Forest Fire
    row5 = pd.Series({
        "distance_to_facility_m": 8000.0,
        "grid_active_days": 1,
        "high_brightness_flag_local": 1,
        "high_frp_flag_local": 0,
        "landcover_class": "Unknown",
        "is_forest_fire_season": 1,
        "is_stubble_burning_season": 0,
    })
    assert assign_weak_label_row(row5) == "Possible Forest Fire"
