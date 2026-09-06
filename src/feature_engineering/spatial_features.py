"""
spatial_features.py — Phase 2C update.

CRS / Distance methodology
--------------------------
Tamil Nadu spans UTM Zone 43N (west of 78°E) and UTM Zone 44N (east of 78°E).
Using a single projected CRS such as EPSG:32643 (UTM 43N) introduces increasing
distortion eastward; at 80.35°E (the eastern boundary of Tamil Nadu) the planar
distortion is non-trivial.

Phase 2C corrects this by using exact WGS84 geodesic distance (Haversine metric)
via scipy BallTree.  This eliminates all UTM-zone projection distortion across
the full extent of Tamil Nadu.

Spatial matching
----------------
Two parallel proximity lookups are performed:
  1. ANY facility    — nearest facility regardless of relevance tier
  2. HIGHER_RELEVANCE — nearest facility that is classified as HIGHER_RELEVANCE
                        (refinery, power plant, steel, cement, mining,
                         oil/gas/chemicals, manufacturing works)

Distance-band indicator columns are produced for both lookups.
"""

import numpy as np
import pandas as pd
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("SpatialFeatures")

EARTH_RADIUS_M = 6_371_000.0  # mean Earth radius used for Haversine distances

FACILITY_MAP = {
    "Power Plant": 1,
    "Industrial Works": 2,
    "Manufacturing": 3,
    "Warehouse/Depot": 4,
    "Construction Materials": 5,
    "Port/Shipyard": 6,
    "Oil & Gas": 7,
    "Mining": 8,
    "Chemical": 9,
    "Other Industrial": 10,
}


def _build_balltree(lat_arr: np.ndarray, lon_arr: np.ndarray):
    """
    Build a sklearn BallTree with Haversine metric from arrays of latitudes and
    longitudes (in decimal degrees).  The tree stores coordinates in radians.
    """
    from sklearn.neighbors import BallTree

    coords_rad = np.radians(np.column_stack([lat_arr, lon_arr]))
    return BallTree(coords_rad, metric="haversine")


def _query_nearest_m(
    tree,
    query_lat: np.ndarray,
    query_lon: np.ndarray,
) -> np.ndarray:
    """
    Query *tree* for the nearest neighbour of each (lat, lon) point.
    Returns distances in **metres**.
    """
    query_rad = np.radians(np.column_stack([query_lat, query_lon]))
    dist_rad, idx = tree.query(query_rad, k=1, return_distance=True)
    dist_m = dist_rad.flatten() * EARTH_RADIUS_M
    return dist_m, idx.flatten()


def compute_spatial_features(
    fires_df: pd.DataFrame, osm_df: pd.DataFrame, config: Config
) -> pd.DataFrame:
    """
    Compute WGS84 geodesic proximity features for each FIRMS detection.

    Two nearest-facility lookups are performed:
      * Any facility (regardless of relevance tier)
      * Higher-relevance facility only (HIGHER_RELEVANCE tier)

    Distance-band indicator columns are created for both.

    Parameters
    ----------
    fires_df : DataFrame with 'latitude' and 'longitude' columns (WGS84).
    osm_df   : DataFrame from OsmRetriever with 'latitude', 'longitude',
               'relevance_tier', 'facility_type', 'name', 'operator',
               'osm_id', 'osm_type' columns.
    config   : project Config object.

    Returns
    -------
    DataFrame (same row count as fires_df) augmented with spatial features.
    """
    logger.info(
        "Computing WGS84 geodesic spatial features "
        "(Haversine BallTree — no UTM projection distortion)..."
    )

    radii = config.spatial.get(
        "distance_radii_m", [500, 1000, 2000, 5000, 10000]
    )
    # Ensure 10 km is always included for reporting
    if 10000 not in radii:
        radii = list(radii) + [10000]

    features = fires_df.reset_index(drop=True).copy()
    fire_lats = features["latitude"].values
    fire_lons = features["longitude"].values

    if osm_df.empty:
        logger.warning(
            "OSM facility DataFrame is empty — spatial features will be NaN."
        )
        _add_empty_spatial_cols(features, radii)
        return features

    # ── 1. ALL facilities ─────────────────────────────────────────────────────
    osm_all = osm_df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    tree_all = _build_balltree(osm_all["latitude"].values, osm_all["longitude"].values)
    dist_any_m, idx_any = _query_nearest_m(tree_all, fire_lats, fire_lons)

    matched_any = osm_all.iloc[idx_any][
        ["osm_id", "osm_type", "facility_type", "normalized_category",
         "relevance_tier", "name", "operator"]
    ].reset_index(drop=True)

    features["distance_to_facility_m"] = dist_any_m
    features["distance_to_facility_km"] = dist_any_m / 1000.0
    features["nearest_facility_osm_id"] = matched_any["osm_id"].values
    features["nearest_facility_osm_type"] = matched_any["osm_type"].values
    features["nearest_facility_name"] = matched_any["name"].values
    features["nearest_facility_type"] = matched_any["facility_type"].values
    features["nearest_facility_category"] = matched_any["normalized_category"].values
    features["nearest_facility_tier"] = matched_any["relevance_tier"].values
    features["industrial_facility_present"] = 1

    for r in radii:
        features[f"near_industrial_{r}m"] = (dist_any_m <= r).astype(int)

    # Legacy column name expected by downstream pipeline
    features["facility_type_code"] = (
        matched_any["facility_type"]
        .map(FACILITY_MAP)
        .fillna(0)
        .astype(int)
        .values
    )

    # ── 2. HIGHER_RELEVANCE facilities only ───────────────────────────────────
    osm_hi = osm_df[
        osm_df["relevance_tier"] == "HIGHER_RELEVANCE"
    ].dropna(subset=["latitude", "longitude"]).reset_index(drop=True)

    if not osm_hi.empty:
        tree_hi = _build_balltree(
            osm_hi["latitude"].values, osm_hi["longitude"].values
        )
        dist_hi_m, idx_hi = _query_nearest_m(tree_hi, fire_lats, fire_lons)
        matched_hi = osm_hi.iloc[idx_hi][
            ["osm_id", "osm_type", "facility_type", "normalized_category", "name"]
        ].reset_index(drop=True)

        features["distance_to_higher_relevance_m"] = dist_hi_m
        features["distance_to_higher_relevance_km"] = dist_hi_m / 1000.0
        features["nearest_higher_relevance_osm_id"] = matched_hi["osm_id"].values
        features["nearest_higher_relevance_name"] = matched_hi["name"].values
        features["nearest_higher_relevance_category"] = matched_hi["normalized_category"].values

        for r in radii:
            features[f"near_higher_relevance_{r}m"] = (dist_hi_m <= r).astype(int)
    else:
        logger.warning(
            "No HIGHER_RELEVANCE facilities found in OSM data. "
            "Higher-relevance proximity columns set to NaN / 0."
        )
        features["distance_to_higher_relevance_m"] = np.nan
        features["distance_to_higher_relevance_km"] = np.nan
        features["nearest_higher_relevance_osm_id"] = np.nan
        features["nearest_higher_relevance_name"] = ""
        features["nearest_higher_relevance_category"] = ""
        for r in radii:
            features[f"near_higher_relevance_{r}m"] = 0

    logger.info(
        f"Spatial feature computation complete. "
        f"Shape: {features.shape}. "
        f"OSM facilities used: {len(osm_all):,} total, "
        f"{len(osm_hi):,} HIGHER_RELEVANCE."
    )
    return features


def _add_empty_spatial_cols(features: pd.DataFrame, radii: list) -> None:
    """Fill spatial columns with NaN / 0 when OSM data is unavailable."""
    for col in [
        "distance_to_facility_m", "distance_to_facility_km",
        "nearest_facility_osm_id", "nearest_facility_osm_type",
        "nearest_facility_name", "nearest_facility_type",
        "nearest_facility_category", "nearest_facility_tier",
        "distance_to_higher_relevance_m", "distance_to_higher_relevance_km",
        "nearest_higher_relevance_osm_id", "nearest_higher_relevance_name",
        "nearest_higher_relevance_category",
    ]:
        features[col] = np.nan
    features["industrial_facility_present"] = 0
    features["facility_type_code"] = 0
    for r in radii:
        features[f"near_industrial_{r}m"] = 0
        features[f"near_higher_relevance_{r}m"] = 0
