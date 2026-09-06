import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
from src.utils.geo_utils import worldcover_tile_name, reproject_gdf, filter_points_by_boundary


def test_worldcover_tile_name():
    # Test positive lat/lon (Tamil Nadu example ~ 11.0 N, 78.0 E)
    assert worldcover_tile_name(11.2, 78.5) == "N09E078"
    assert worldcover_tile_name(9.0, 78.0) == "N09E078"
    assert worldcover_tile_name(12.5, 80.1) == "N12E078"

    # Test negative coordinates
    assert worldcover_tile_name(-5.0, -40.0) == "S06W042"


def test_reproject_gdf():
    points = [Point(78.0, 11.0), Point(78.5, 11.5)]
    gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")
    reprojected = reproject_gdf(gdf, "EPSG:32643")
    assert reprojected.crs.to_string() == "EPSG:32643"
    assert reprojected.geometry.iloc[0].x != 78.0


def test_filter_points_by_boundary():
    # Create simple 1x1 degree square boundary
    poly = Polygon([(78.0, 10.0), (79.0, 10.0), (79.0, 11.0), (78.0, 11.0)])
    boundary = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")

    df = pd.DataFrame({
        "latitude": [10.5, 12.0, 10.1],
        "longitude": [78.5, 78.5, 77.0],
        "id": [1, 2, 3]
    })

    filtered, bbox = filter_points_by_boundary(df, boundary)
    assert len(filtered) == 1
    assert filtered["id"].iloc[0] == 1
    assert bbox == (78.0, 10.0, 79.0, 11.0)
