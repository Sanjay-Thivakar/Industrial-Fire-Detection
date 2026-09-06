import numpy as np
import pandas as pd
import geopandas as gpd
from typing import Tuple

def reproject_gdf(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    """Safely reproject a GeoDataFrame to a target CRS."""
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    if gdf.crs != target_crs:
        return gdf.to_crs(target_crs)
    return gdf

def filter_points_by_boundary(
    df: pd.DataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude"
) -> Tuple[pd.DataFrame, Tuple[float, float, float, float]]:
    """
    Filter points DataFrame to a boundary polygon.
    First applies bounding box filter, then spatial within test.
    Returns filtered DataFrame and bounding box coordinates (minx, miny, maxx, maxy).
    """
    boundary = reproject_gdf(boundary_gdf, "EPSG:4326")
    minx, miny, maxx, maxy = boundary.total_bounds
    
    bbox_mask = df[lon_col].between(minx, maxx) & df[lat_col].between(miny, maxy)
    candidates = df[bbox_mask].copy()
    
    if candidates.empty:
        return pd.DataFrame(columns=df.columns), (minx, miny, maxx, maxy)
        
    points_gdf = gpd.GeoDataFrame(
        candidates,
        geometry=gpd.points_from_xy(candidates[lon_col], candidates[lat_col]),
        crs="EPSG:4326"
    )
    
    union_poly = boundary.geometry.union_all()
    inside_mask = points_gdf.geometry.within(union_poly)
    
    filtered_df = candidates[inside_mask].reset_index(drop=True)
    return filtered_df, (minx, miny, maxx, maxy)

def worldcover_tile_name(lat: float, lon: float) -> str:
    """
    Determine ESA WorldCover 3x3 degree tile name based on lower-left lat/lon corner.
    Example: (11.0, 78.0) -> 'N09E078' (lower-left of 9..12 lat, 78..81 lon)
    """
    lat_tile = int(np.floor(lat / 3.0) * 3)
    lon_tile = int(np.floor(lon / 3.0) * 3)
    ns = "N" if lat_tile >= 0 else "S"
    ew = "E" if lon_tile >= 0 else "W"
    return f"{ns}{abs(lat_tile):02d}{ew}{abs(lon_tile):03d}"
