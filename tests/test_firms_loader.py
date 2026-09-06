import os
import zipfile
import pytest
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Polygon
from src.config import Config
from src.data_ingestion.firms_loader import FirmsLoader
from src.utils.geo_utils import filter_points_by_boundary


def test_chunked_firms_ingestion_and_bbox_filtering(tmp_path):
    # Create synthetic raw directory structure
    raw_dir = tmp_path / "data" / "raw" / "firms"
    n20_dir = raw_dir / "viirs_noaa20"
    n20_dir.mkdir(parents=True, exist_ok=True)

    # Generate synthetic CSV with points inside and outside Tamil Nadu bbox
    # TN BBox ~ lon [76.23, 80.35], lat [8.08, 13.54]
    df = pd.DataFrame({
        "latitude": [11.0, 12.0, 25.0, 10.0, -999.0],  # 11.0 & 12.0 inside, 25.0 outside TN, 10.0 inside, -999 invalid
        "longitude": [78.0, 79.0, 85.0, 78.0, 78.0],
        "brightness": [320.0, 330.0, 310.0, 315.0, 300.0],
        "bright_t31": [290.0, 295.0, 290.0, 290.0, 290.0],
        "frp": [15.0, 25.0, 10.0, 12.0, 5.0],
        "scan": [0.4, 0.4, 0.4, 0.4, 0.4],
        "track": [0.4, 0.4, 0.4, 0.4, 0.4],
        "acq_date": ["2023-01-01"] * 5,
        "acq_time": [1200] * 5,
        "confidence": ["h"] * 5,
    })

    csv_path = n20_dir / "fire_nrt_J1V-C2_test.csv"
    df.to_csv(csv_path, index=False)

    # Initialize Config pointing to tmp_path
    config_dict = {
        "paths": {
            "raw_dir": "data/raw",
            "cache_dir": "data/cache",
            "output_dir": "outputs",
        },
        "firms": {
            "chunk_size": 2,  # Small chunk size to force multiple chunks
            "primary_sensors": [
                {"name": "VIIRS_N20", "pattern": "J1V-C2"},
                {"name": "VIIRS_SUOMI_NPP", "pattern": "SV-C2"},
                {"name": "VIIRS_NOAA21", "pattern": "J2V-C2"},
            ],
            "extensible_sensors": [
                {"name": "MODIS", "pattern": "M-C61", "include_in_baseline": False}
            ]
        }
    }
    config = Config(config_dict, project_root=tmp_path)

    loader = FirmsLoader(config)
    result_df = loader.load_and_clean_firms(target_bbox=(76.23, 8.08, 80.35, 13.54))

    # Verify rows surviving coordinate validation and bbox pre-filter
    # Lat 11.0, 12.0, 10.0 survive (3 rows). Lat 25.0 filtered out by bbox, -999.0 filtered out by coord validation.
    assert len(result_df) == 3
    assert set(result_df["latitude"]) == {11.0, 12.0, 10.0}
    assert result_df["satellite_source"].iloc[0] == "VIIRS_N20"


def test_polygon_filtering():
    # Polygon filtering test against a mock state boundary
    poly = Polygon([(77.0, 9.0), (80.0, 9.0), (80.0, 13.0), (77.0, 13.0)])
    boundary_gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")

    df = pd.DataFrame({
        "latitude": [11.0, 15.0],  # 11.0 inside polygon, 15.0 outside
        "longitude": [78.0, 78.0],
        "brightness": [320.0, 310.0],
        "frp": [10.0, 5.0],
    })

    filtered, bbox = filter_points_by_boundary(df, boundary_gdf)
    assert len(filtered) == 1
    assert filtered["latitude"].iloc[0] == 11.0
    assert bbox == (77.0, 9.0, 80.0, 13.0)
