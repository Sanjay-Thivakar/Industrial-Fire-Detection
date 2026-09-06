import numpy as np
import pandas as pd
from pathlib import Path
from src.config import Config
from src.utils.logger import setup_logger
from src.utils.geo_utils import worldcover_tile_name

logger = setup_logger("LandcoverSampler")

DEFAULT_CLASS_MAP = {
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


def sample_landcover(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """
    Samples ESA WorldCover 10m land cover class at point locations via direct S3 range-read.
    Caches results locally and degrades gracefully if remote raster access fails.
    """
    logger.info("Sampling ESA WorldCover land cover data...")
    features = df.reset_index(drop=True).copy()
    features["row_id"] = features.index

    cache_file = config.cache_dir / config.landcover.get("cache_file", "landcover_tn_sampled.csv")
    class_map = config.landcover.get("class_map", DEFAULT_CLASS_MAP)
    # Ensure keys in class_map are integers
    class_map = {int(k): str(v) for k, v in class_map.items()}

    if cache_file.exists():
        logger.info(f"Loading cached land cover sampling from {cache_file}")
        lc_df = pd.read_csv(cache_file)
    else:
        if not config.landcover.get("enabled", True):
            logger.info("Landcover sampling disabled in configuration. Skipping remote fetch.")
            lc_df = pd.DataFrame({"row_id": features["row_id"], "landcover_code": [np.nan] * len(features)})
        else:
            try:
                import rasterio

                coords = features[["latitude", "longitude"]].reset_index(drop=True)
                coords["tile"] = coords.apply(
                    lambda r: worldcover_tile_name(r["latitude"], r["longitude"]), axis=1
                )

                unique_tiles = coords["tile"].unique()
                logger.info(f"Points span {len(unique_tiles)} ESA WorldCover tile(s): {list(unique_tiles)}")

                results = {}
                base_url = config.landcover.get(
                    "s3_url_template",
                    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
                )

                for tile in unique_tiles:
                    # Use the HTTPS URL directly — rasterio passes it to GDAL's
                    # built-in /vsicurl/ handler internally.  Prepending the
                    # /vsicurl/ prefix manually to an https:// URL creates a
                    # double VSI prefix that causes stale reads or hangs.
                    url = base_url.format(tile=tile)
                    tile_points = coords[coords["tile"] == tile]
                    logger.info(f"Sampling {len(tile_points)} points from remote S3 tile {tile}...")

                    try:
                        with rasterio.open(url) as src:
                            sample_coords = list(zip(tile_points["longitude"], tile_points["latitude"]))
                            values = list(src.sample(sample_coords))
                            for idx, val in zip(tile_points.index, values):
                                results[idx] = int(val[0]) if val is not None else np.nan
                    except Exception as tile_err:
                        logger.warning(f"Could not read tile {tile}: {tile_err}")
                        for idx in tile_points.index:
                            results[idx] = np.nan

                lc_df = pd.DataFrame({
                    "row_id": list(results.keys()),
                    "landcover_code": list(results.values()),
                }).sort_values("row_id").reset_index(drop=True)

                lc_df.to_csv(cache_file, index=False)
                logger.info(f"Land cover sampling cached to {cache_file}")

            except Exception as e:
                logger.warning(f"Remote land cover sampling failed ({e}). Proceeding with landcover as 'Unknown'.")
                lc_df = pd.DataFrame({"row_id": features["row_id"], "landcover_code": [np.nan] * len(features)})

    features = features.merge(lc_df, on="row_id", how="left")
    features["landcover_class"] = features["landcover_code"].map(class_map).fillna("Unknown")

    logger.info("Land cover distribution:")
    logger.info(features["landcover_class"].value_counts().to_dict())

    return features
