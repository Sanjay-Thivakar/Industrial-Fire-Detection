"""
phase2c_finalize.py
====================
Phase 2C finalisation script.

Uses the already-populated caches:
  - data/cache/landcover_tn_sampled.csv   (633 rows, 100% valid)
  - data/cache/osm_industrial_facilities.json  (11,429 unique facilities)

Performs:
  1. Load & verify WorldCover cache (no re-fetch needed)
  2. Load & verify OSM cache (no re-fetch needed)
  3. Compute WGS84 geodesic spatial proximity features for all 633 events
  4. Build thermal / temporal features
  5. Run known-facility sanity checks (7 TN industrial hubs)
  6. Score & rank all 633 FIRMS events as validation candidates
  7. Export validation_candidates_v2.csv (all 633, UNVERIFIED)
  8. Export validation_batch_v1.csv (≈100 diverse events, UNVERIFIED)
  9. Print statistics for the Phase 2C reports

STOP conditions enforced:
  - No Random Forest retraining
  - No automatic ground-truth labeling
  - All candidates remain ground_truth_status = UNVERIFIED
"""

import sys
import json
import logging
import warnings
import time
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree
from scipy import stats

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Phase2CFinalize")

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
CACHE_DIR = BASE / "data" / "cache"
OUT_DIR = BASE / "outputs" / "ground_truth_investigation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIRMS_CACHE = CACHE_DIR / "VIIRS_primary_clean.csv"
WC_CACHE = CACHE_DIR / "landcover_tn_sampled.csv"
OSM_JSON = CACHE_DIR / "osm_industrial_facilities.json"
OSM_CSV = BASE / "outputs" / "OSM_Industrial_Facilities.csv"

EARTH_RADIUS_M = 6_371_000.0

# Known Tamil Nadu industrial facilities for sanity checks
KNOWN_FACILITIES = [
    {"name": "Mettur Thermal Power Station",  "lat": 11.800, "lon": 77.800},
    {"name": "Salem Steel Plant",             "lat": 11.650, "lon": 78.140},
    {"name": "Neyveli Lignite Corporation",   "lat": 11.596, "lon": 79.488},
    {"name": "Ariyalur Cement Cluster",       "lat": 11.130, "lon": 79.080},
    {"name": "Manali/Chennai Industrial Corridor", "lat": 13.165, "lon": 80.260},
    {"name": "Tuticorin Industrial/Port Region",   "lat": 8.764,  "lon": 78.130},
    {"name": "Ennore Industrial/Power Region",     "lat": 13.208, "lon": 80.323},
]


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Load FIRMS events
# ──────────────────────────────────────────────────────────────────────────────
def load_firms():
    logger.info(f"Loading FIRMS dataset: {FIRMS_CACHE}")
    df = pd.read_csv(FIRMS_CACHE)

    # Filter using the Tamil Nadu state boundary polygon (more precise than bbox)
    boundary_path = CACHE_DIR / "tamil_nadu_boundary.geojson"
    if boundary_path.exists():
        import geopandas as gpd
        boundary = gpd.read_file(boundary_path)
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
            crs="EPSG:4326"
        )
        within = gpd.sjoin(gdf, boundary[["geometry"]], how="inner", predicate="within")
        df = within.drop(columns=["geometry", "index_right"], errors="ignore")
        df = df.drop_duplicates(subset=["latitude", "longitude", "acq_date", "acq_time"])
        df = df.reset_index(drop=True)
        logger.info(f"Retained {len(df)} FIRMS events inside Tamil Nadu state boundary polygon")
    else:
        # Fallback to bounding box
        logger.warning("Tamil Nadu boundary geojson not found — falling back to bbox filter")
        TN_BBOX = (76.23, 8.08, 80.35, 13.54)
        mask = (
            (df["longitude"] >= TN_BBOX[0]) & (df["longitude"] <= TN_BBOX[2]) &
            (df["latitude"]  >= TN_BBOX[1]) & (df["latitude"]  <= TN_BBOX[3])
        )
        df = df[mask].reset_index(drop=True)
        logger.info(f"Retained {len(df)} FIRMS events inside Tamil Nadu bbox")

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Verify WorldCover cache
# ──────────────────────────────────────────────────────────────────────────────
CLASS_MAP = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare/sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

def load_worldcover(fires_df):
    logger.info(f"Loading WorldCover cache: {WC_CACHE}")
    wc = pd.read_csv(WC_CACHE)
    wc["landcover_class"] = wc["landcover_code"].map(CLASS_MAP).fillna("Unknown")
    fires_df = fires_df.reset_index(drop=True)
    fires_df["row_id"] = fires_df.index
    merged = fires_df.merge(wc[["row_id", "landcover_code", "landcover_class"]], on="row_id", how="left")
    merged["landcover_class"] = merged["landcover_class"].fillna("Unknown")
    n_valid = (merged["landcover_class"] != "Unknown").sum()
    n_unknown = (merged["landcover_class"] == "Unknown").sum()
    logger.info(f"WorldCover: {n_valid}/{len(merged)} valid ({100*n_valid/len(merged):.2f}%), "
                f"Unknown={n_unknown} ({100*n_unknown/len(merged):.2f}%)")
    logger.info(f"WorldCover distribution: {merged['landcover_class'].value_counts().to_dict()}")
    return merged


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: Load OSM facilities
# ──────────────────────────────────────────────────────────────────────────────
def load_osm():
    logger.info(f"Loading OSM CSV: {OSM_CSV}")
    osm = pd.read_csv(OSM_CSV)
    logger.info(f"OSM facilities loaded: {len(osm):,}")
    logger.info(f"Relevance tier distribution: {osm['relevance_tier'].value_counts().to_dict()}")
    logger.info(f"Category distribution: {osm['normalized_category'].value_counts().to_dict()}")

    # Load tile report
    with open(OSM_JSON) as f:
        osm_meta = json.load(f)
    tile_report = pd.DataFrame(osm_meta.get("tile_report", []))
    n_success = tile_report["success"].sum() if not tile_report.empty else 0
    n_total = len(tile_report)
    logger.info(f"Tile report: {n_success}/{n_total} tiles succeeded")
    return osm, tile_report


# ──────────────────────────────────────────────────────────────────────────────
# Step 4: Compute WGS84 geodesic spatial features (Haversine BallTree)
# ──────────────────────────────────────────────────────────────────────────────
RADII = [500, 1000, 2000, 5000, 10000]

def compute_spatial_features(fires_df, osm_df):
    logger.info("Computing WGS84 geodesic spatial proximity features (Haversine BallTree)...")

    fire_lats = fires_df["latitude"].values
    fire_lons = fires_df["longitude"].values
    fire_rad = np.radians(np.column_stack([fire_lats, fire_lons]))

    # ── ANY facility ──────────────────────────────────────────────────────────
    osm_all = osm_df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    coords_rad = np.radians(osm_all[["latitude", "longitude"]].values)
    tree_all = BallTree(coords_rad, metric="haversine")
    dist_rad, idx_all = tree_all.query(fire_rad, k=1, return_distance=True)
    dist_any_m = dist_rad.flatten() * EARTH_RADIUS_M
    idx_all = idx_all.flatten()

    matched = osm_all.iloc[idx_all][
        ["osm_id", "osm_type", "name", "facility_type",
         "normalized_category", "relevance_tier", "operator"]
    ].reset_index(drop=True)

    fires_df = fires_df.copy()
    fires_df["distance_to_facility_m"]    = dist_any_m
    fires_df["distance_to_facility_km"]   = dist_any_m / 1000.0
    fires_df["nearest_facility_name"]     = matched["name"].values
    fires_df["nearest_facility_type"]     = matched["facility_type"].values
    fires_df["nearest_facility_category"] = matched["normalized_category"].values
    fires_df["nearest_facility_tier"]     = matched["relevance_tier"].values
    fires_df["nearest_facility_osm_id"]   = matched["osm_id"].values
    fires_df["nearest_facility_operator"] = matched["operator"].values

    for r in RADII:
        fires_df[f"near_industrial_{r}m"] = (dist_any_m <= r).astype(int)

    # ── HIGHER_RELEVANCE only ─────────────────────────────────────────────────
    osm_hi = osm_df[osm_df["relevance_tier"] == "HIGHER_RELEVANCE"].dropna(
        subset=["latitude", "longitude"]
    ).reset_index(drop=True)

    if not osm_hi.empty:
        coords_hi = np.radians(osm_hi[["latitude", "longitude"]].values)
        tree_hi = BallTree(coords_hi, metric="haversine")
        dist_hi_rad, idx_hi = tree_hi.query(fire_rad, k=1, return_distance=True)
        dist_hi_m = dist_hi_rad.flatten() * EARTH_RADIUS_M
        idx_hi = idx_hi.flatten()
        matched_hi = osm_hi.iloc[idx_hi][
            ["osm_id", "name", "normalized_category"]
        ].reset_index(drop=True)
        fires_df["distance_to_higher_relevance_m"]   = dist_hi_m
        fires_df["distance_to_higher_relevance_km"]  = dist_hi_m / 1000.0
        fires_df["nearest_higher_relevance_name"]    = matched_hi["name"].values
        fires_df["nearest_higher_relevance_category"]= matched_hi["normalized_category"].values
        for r in RADII:
            fires_df[f"near_higher_relevance_{r}m"] = (dist_hi_m <= r).astype(int)
    else:
        fires_df["distance_to_higher_relevance_m"]   = np.nan
        fires_df["distance_to_higher_relevance_km"]  = np.nan
        fires_df["nearest_higher_relevance_name"]    = ""
        fires_df["nearest_higher_relevance_category"]= ""
        for r in RADII:
            fires_df[f"near_higher_relevance_{r}m"] = 0

    logger.info(f"Spatial feature computation complete. Shape: {fires_df.shape}")

    # Print proximity statistics
    for r in RADII:
        n = fires_df[f"near_industrial_{r}m"].sum()
        n_hi = fires_df[f"near_higher_relevance_{r}m"].sum()
        logger.info(
            f"  Within {r/1000:.1f} km — ANY: {n}/{len(fires_df)} ({100*n/len(fires_df):.1f}%)  "
            f"HIGHER_RELEVANCE: {n_hi}/{len(fires_df)} ({100*n_hi/len(fires_df):.1f}%)"
        )

    return fires_df


# ──────────────────────────────────────────────────────────────────────────────
# Step 5: Thermal / temporal features
# ──────────────────────────────────────────────────────────────────────────────
def compute_thermal_temporal_features(df):
    logger.info("Computing thermal and temporal features...")

    # Acquire date / time columns
    if "acq_date" in df.columns:
        df["acq_datetime"] = pd.to_datetime(df["acq_date"].astype(str), errors="coerce")
        df["month"] = df["acq_datetime"].dt.month
        df["day_of_year"] = df["acq_datetime"].dt.dayofyear
    else:
        df["month"] = np.nan
        df["day_of_year"] = np.nan

    # Daytime flag from scan time
    if "acq_time" in df.columns:
        df["is_daytime"] = (df["acq_time"].astype(str).str.zfill(4).str[:2].astype(float) >= 6) & \
                           (df["acq_time"].astype(str).str.zfill(4).str[:2].astype(float) <= 18)
        df["is_daytime"] = df["is_daytime"].astype(int)
    else:
        df["is_daytime"] = np.nan

    # FRP normalisation
    if "frp" in df.columns:
        frp = df["frp"].values.astype(float)
        df["frp_log1p"] = np.log1p(frp)
        df["frp_zscore"] = stats.zscore(frp, nan_policy="omit")
    else:
        df["frp_log1p"] = np.nan
        df["frp_zscore"] = np.nan

    # Grid-cell persistence (count of events in same 0.01° grid cell)
    if "latitude" in df.columns and "longitude" in df.columns:
        df["grid_lat"] = (df["latitude"] / 0.01).round().astype(int)
        df["grid_lon"] = (df["longitude"] / 0.01).round().astype(int)
        df["grid_count"] = df.groupby(["grid_lat", "grid_lon"])["grid_lat"].transform("count")
    else:
        df["grid_count"] = 1

    logger.info("Thermal/temporal features computed.")
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 6: Known facility sanity checks
# ──────────────────────────────────────────────────────────────────────────────
def run_sanity_checks(osm_df):
    logger.info("\n=== Known Facility Sanity Checks ===")
    osm_coords = np.radians(osm_df[["latitude", "longitude"]].values)
    tree = BallTree(osm_coords, metric="haversine")

    results = []
    for kf in KNOWN_FACILITIES:
        q = np.radians([[kf["lat"], kf["lon"]]])
        dist_rad, idx = tree.query(q, k=3, return_distance=True)
        dist_m = dist_rad.flatten() * EARTH_RADIUS_M
        nearby = osm_df.iloc[idx.flatten()][
            ["name", "normalized_category", "relevance_tier", "latitude", "longitude"]
        ].reset_index(drop=True)
        nearby["distance_m"] = dist_m

        match_found = dist_m[0] <= 10000  # within 10 km
        result = {
            "known_facility": kf["name"],
            "search_lat": kf["lat"],
            "search_lon": kf["lon"],
            "match_found_within_10km": match_found,
            "nearest_osm_name": nearby.iloc[0]["name"] if match_found else "NONE",
            "nearest_osm_category": nearby.iloc[0]["normalized_category"] if match_found else "N/A",
            "nearest_distance_m": round(dist_m[0], 0),
        }
        results.append(result)
        status = "✓ FOUND" if match_found else "✗ NOT FOUND within 10 km"
        logger.info(
            f"  {kf['name']}: {status} "
            f"(nearest={result['nearest_osm_name']!r}, {result['nearest_distance_m']:.0f} m, "
            f"category={result['nearest_osm_category']})"
        )
    return pd.DataFrame(results)


# ──────────────────────────────────────────────────────────────────────────────
# Step 7: Candidate priority scoring
# ──────────────────────────────────────────────────────────────────────────────
def compute_candidate_priority(df):
    """
    Multi-criteria priority score for selecting a DIVERSE human-validation batch.
    Score components (each 0–1 normalised):
      - FRP intensity (higher = higher priority)
      - Proximity to HIGHER_RELEVANCE facility (closer = higher priority)
      - Grid persistence (both high AND low are interesting)
      - Land cover (built-up = higher; cropland/grassland = moderately high for agriculture context)
    """
    logger.info("Computing candidate priority scores...")

    scores = pd.Series(0.0, index=df.index)

    # FRP component
    if "frp" in df.columns:
        frp = df["frp"].fillna(0).values.astype(float)
        frp_norm = (frp - frp.min()) / (frp.max() - frp.min() + 1e-9)
        scores += 0.30 * frp_norm

    # Higher-relevance proximity (closer = higher score)
    if "distance_to_higher_relevance_m" in df.columns:
        d = df["distance_to_higher_relevance_m"].fillna(50000).values.astype(float)
        # Inverse-distance, clamped at 50 km
        d = np.minimum(d, 50000)
        prox = 1.0 - (d / 50000)
        scores += 0.35 * prox

    # ANY facility proximity
    if "distance_to_facility_m" in df.columns:
        d_any = df["distance_to_facility_m"].fillna(50000).values.astype(float)
        d_any = np.minimum(d_any, 50000)
        prox_any = 1.0 - (d_any / 50000)
        scores += 0.10 * prox_any

    # Persistence (grid_count)
    if "grid_count" in df.columns:
        gc = df["grid_count"].fillna(1).values.astype(float)
        gc_norm = (gc - gc.min()) / (gc.max() - gc.min() + 1e-9)
        scores += 0.15 * gc_norm

    # Land cover bonus
    lc_bonus = {
        "Built-up": 0.10, "Shrubland": 0.05, "Grassland": 0.05,
        "Cropland": 0.07, "Tree cover": 0.03,
    }
    if "landcover_class" in df.columns:
        lc_scores = df["landcover_class"].map(lc_bonus).fillna(0.0)
        scores += lc_scores

    df["candidate_priority_score"] = scores.clip(0, 1)
    df["candidate_priority_rank"] = df["candidate_priority_score"].rank(
        ascending=False, method="first"
    ).astype(int)

    # Validation status (MANDATORY: UNVERIFIED)
    df["ground_truth_status"] = "UNVERIFIED"
    df["validation_label"] = ""
    df["validation_confidence"] = ""
    df["validation_notes"] = ""

    logger.info(
        f"Priority scoring complete. "
        f"Score range: [{df['candidate_priority_score'].min():.4f}, "
        f"{df['candidate_priority_score'].max():.4f}]"
    )
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 8: Select diverse validation batch (~100 events)
# ──────────────────────────────────────────────────────────────────────────────
def select_diverse_batch(df, target_n=100):
    """
    Select a DIVERSE VALIDATION BATCH (NOT a balanced or stratified sample).
    Goal: maximize diversity across:
      - industrial proximity
      - FRP intensity
      - landcover
      - geographic region (lat/lon)
      - season / month
      - sensor / day-night
      - ambiguous, agricultural, and natural-fire contexts
    """
    logger.info(f"Selecting diverse validation batch (target n={target_n})...")

    # Define strata for diversity sampling
    batch_indices = set()

    # Pool A: Top-priority industrial-proximate events (≤2 km HIGHER_RELEVANCE)
    pool_a = df[df.get("distance_to_higher_relevance_m", pd.Series(dtype=float)).fillna(999999) <= 2000]
    n_a = min(25, len(pool_a))
    if n_a > 0:
        batch_indices.update(pool_a.nlargest(n_a, "candidate_priority_score").index)

    # Pool B: Top-priority ANY facility ≤2 km
    pool_b = df[df["distance_to_facility_m"].fillna(999999) <= 2000]
    n_b = min(15, len(pool_b))
    if n_b > 0:
        batch_indices.update(pool_b.nlargest(n_b, "candidate_priority_score").index)

    # Pool C: High FRP events (top 20 by FRP)
    if "frp" in df.columns:
        pool_c = df.nlargest(20, "frp")
        batch_indices.update(pool_c.index)

    # Pool D: Built-up landcover context
    if "landcover_class" in df.columns:
        pool_d = df[df["landcover_class"] == "Built-up"]
        n_d = min(10, len(pool_d))
        if n_d > 0:
            batch_indices.update(pool_d.sample(min(n_d, len(pool_d)), random_state=42).index)

        # Pool E: Agricultural context (Cropland / Grassland)
        pool_e = df[df["landcover_class"].isin(["Cropland", "Grassland"])]
        n_e = min(10, len(pool_e))
        if n_e > 0:
            batch_indices.update(pool_e.sample(min(n_e, len(pool_e)), random_state=42).index)

        # Pool F: Natural/forest context (Tree cover / Shrubland)
        pool_f = df[df["landcover_class"].isin(["Tree cover", "Shrubland"])]
        n_f = min(8, len(pool_f))
        if n_f > 0:
            batch_indices.update(pool_f.sample(min(n_f, len(pool_f)), random_state=42).index)

    # Pool G: Ambiguous cases (moderate FRP, mid-range proximity, mixed landcover)
    if "frp" in df.columns:
        frp_median = df["frp"].median()
        pool_g = df[
            (df["frp"] >= frp_median * 0.5) &
            (df["frp"] <= frp_median * 2.0) &
            (df["distance_to_facility_m"].fillna(999999) > 2000) &
            (df["distance_to_facility_m"].fillna(999999) <= 10000)
        ]
        n_g = min(8, len(pool_g))
        if n_g > 0:
            batch_indices.update(pool_g.sample(min(n_g, len(pool_g)), random_state=42).index)

    # Pool H: Geographic diversity — stratify by lat/lon deciles
    lat_deciles = pd.qcut(df["latitude"], q=5, labels=False, duplicates="drop")
    lon_deciles = pd.qcut(df["longitude"], q=5, labels=False, duplicates="drop")
    for lat_bin in lat_deciles.unique():
        for lon_bin in lon_deciles.unique():
            subset = df[(lat_deciles == lat_bin) & (lon_deciles == lon_bin)]
            if not subset.empty and len(batch_indices) < target_n:
                batch_indices.add(subset.nlargest(1, "candidate_priority_score").index[0])

    # Top-up to target_n from priority ranking
    remaining_needed = target_n - len(batch_indices)
    if remaining_needed > 0:
        top_up = df.nlargest(target_n + 50, "candidate_priority_score")
        for idx in top_up.index:
            if idx not in batch_indices:
                batch_indices.add(idx)
                remaining_needed -= 1
                if remaining_needed <= 0:
                    break

    batch = df.loc[sorted(batch_indices)].copy()
    logger.info(f"Diverse validation batch selected: {len(batch)} events")

    # Summarise batch diversity
    if "landcover_class" in batch.columns:
        logger.info(f"  Landcover distribution: {batch['landcover_class'].value_counts().to_dict()}")
    if "distance_to_facility_m" in batch.columns:
        for r in [500, 1000, 2000, 5000, 10000]:
            n = (batch["distance_to_facility_m"] <= r).sum()
            logger.info(f"  Within {r/1000:.1f} km of ANY facility: {n}/{len(batch)}")

    return batch


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("PHASE 2C FINALIZATION — SPATIAL PROCESSING & CANDIDATE CURATION")
    logger.info("=" * 70)

    # 1. FIRMS
    fires = load_firms()
    assert len(fires) == 633, f"Expected 633 FIRMS events, got {len(fires)}"

    # 2. WorldCover
    fires = load_worldcover(fires)

    # 3. OSM
    osm, tile_report = load_osm()

    # 4. Spatial features
    fires = compute_spatial_features(fires, osm)

    # 5. Thermal/temporal features
    fires = compute_thermal_temporal_features(fires)

    # 6. Sanity checks
    sanity_df = run_sanity_checks(osm)
    sanity_path = OUT_DIR / "known_facility_sanity_check.csv"
    sanity_df.to_csv(sanity_path, index=False)
    logger.info(f"Sanity check results saved to {sanity_path}")

    # 7. Candidate priority
    fires = compute_candidate_priority(fires)

    # 8. Export validation_candidates_v2.csv (all 633)
    fires["ground_truth_status"] = "UNVERIFIED"
    cand_path = OUT_DIR / "validation_candidates_v2.csv"
    fires.to_csv(cand_path, index=False)
    logger.info(f"Exported validation_candidates_v2.csv: {len(fires)} rows → {cand_path}")

    # 9. Select diverse validation batch
    batch = select_diverse_batch(fires, target_n=100)
    batch["ground_truth_status"] = "UNVERIFIED"
    batch_path = OUT_DIR / "validation_batch_v1.csv"
    batch.to_csv(batch_path, index=False)
    logger.info(f"Exported validation_batch_v1.csv: {len(batch)} rows → {batch_path}")

    # 10. Print summary statistics for reports
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2C FINAL STATISTICS SUMMARY")
    logger.info("=" * 70)

    logger.info(f"\nFIRMS events: {len(fires)}")
    logger.info(f"WorldCover valid: {(fires['landcover_class'] != 'Unknown').sum()} / {len(fires)} ({100*(fires['landcover_class'] != 'Unknown').mean():.2f}%)")
    logger.info(f"WorldCover Unknown: {(fires['landcover_class'] == 'Unknown').sum()}")
    logger.info(f"\nWorldCover distribution:\n{fires['landcover_class'].value_counts().to_string()}")

    logger.info(f"\nOSM facilities (total unique): {len(osm):,}")
    logger.info(f"OSM tile report:\n{tile_report.to_string() if not tile_report.empty else 'N/A'}")
    logger.info(f"\nOSM relevance tier distribution:\n{osm['relevance_tier'].value_counts().to_string()}")
    logger.info(f"\nOSM category distribution:\n{osm['normalized_category'].value_counts().to_string()}")

    logger.info(f"\nProximity statistics (ALL facilities):")
    for r in RADII:
        n = fires[f"near_industrial_{r}m"].sum()
        logger.info(f"  ≤ {r/1000:.1f} km: {n} events ({100*n/len(fires):.1f}%)")

    logger.info(f"\nProximity statistics (HIGHER_RELEVANCE only):")
    for r in RADII:
        col = f"near_higher_relevance_{r}m"
        if col in fires.columns:
            n = fires[col].sum()
            logger.info(f"  ≤ {r/1000:.1f} km: {n} events ({100*n/len(fires):.1f}%)")

    logger.info(f"\nDistance to nearest ANY facility (m):")
    logger.info(f"  min={fires['distance_to_facility_m'].min():.0f}  "
                f"median={fires['distance_to_facility_m'].median():.0f}  "
                f"p75={fires['distance_to_facility_m'].quantile(0.75):.0f}  "
                f"p90={fires['distance_to_facility_m'].quantile(0.90):.0f}  "
                f"max={fires['distance_to_facility_m'].max():.0f}")

    logger.info(f"\nDistance to nearest HIGHER_RELEVANCE facility (m):")
    hi_d = fires["distance_to_higher_relevance_m"].dropna()
    if len(hi_d) > 0:
        logger.info(f"  min={hi_d.min():.0f}  median={hi_d.median():.0f}  "
                    f"p75={hi_d.quantile(0.75):.0f}  p90={hi_d.quantile(0.90):.0f}  "
                    f"max={hi_d.max():.0f}")

    logger.info(f"\nValidation batch size: {len(batch)}")
    logger.info(f"All candidates ground_truth_status = UNVERIFIED: "
                f"{(fires['ground_truth_status'] == 'UNVERIFIED').all()}")

    elapsed = time.time() - t0
    logger.info(f"\nPhase 2C finalization completed in {elapsed:.1f} seconds.")
    logger.info("=" * 70)
    logger.info("PHASE 2C COMPLETE.")
    logger.info("Next step: Human review of PHASE_2C_CORRECTION_AND_CURATION_REPORT.md")
    logger.info("DO NOT retrain the Random Forest. DO NOT apply automatic ground-truth labels.")
    logger.info("=" * 70)

    return fires, batch, osm, tile_report, sanity_df


if __name__ == "__main__":
    fires, batch, osm, tile_report, sanity_df = main()
