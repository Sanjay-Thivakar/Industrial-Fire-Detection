import zipfile
import requests
import geopandas as gpd
from pathlib import Path
from src.config import Config
from src.utils.logger import setup_logger
from src.utils.geo_utils import reproject_gdf

logger = setup_logger("BoundaryLoader")


class BoundaryLoader:
    """Loads and caches administrative boundary polygons (e.g. Tamil Nadu)."""

    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.cache_dir
        self.region_name = config.region.get("name", "Tamil Nadu")
        self.cache_filename = config.region.get("boundary_cache", "tamil_nadu_boundary.geojson")
        self.ne_url = config.region.get(
            "fallback_natural_earth_url",
            "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip"
        )

    def load_boundary(self) -> gpd.GeoDataFrame:
        """Load target region boundary GeoDataFrame from cache or Natural Earth S3."""
        cache_path = self.cache_dir / self.cache_filename

        if cache_path.exists():
            logger.info(f"Loading cached boundary from: {cache_path}")
            boundary_gdf = gpd.read_file(cache_path)
            return reproject_gdf(boundary_gdf, "EPSG:4326")

        logger.info(f"Boundary cache not found. Downloading Natural Earth admin-1 shapefiles from {self.ne_url}")
        ne_zip_path = self.cache_dir / "ne_admin1.zip"
        r = requests.get(self.ne_url, timeout=180)
        r.raise_for_status()
        ne_zip_path.write_bytes(r.content)

        ne_extract_dir = self.cache_dir / "ne_admin1"
        ne_extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(ne_zip_path, "r") as z:
            z.extractall(ne_extract_dir)

        shp_files = list(ne_extract_dir.rglob("*.shp"))
        if not shp_files:
            raise RuntimeError("Natural Earth admin-1 shapefile not found in extracted ZIP archive.")

        states_gdf = gpd.read_file(shp_files[0])
        name_col = next((c for c in ["name", "NAME", "woe_name", "gn_name"] if c in states_gdf.columns), None)
        if name_col is None:
            raise RuntimeError("Could not identify state name column in shapefile.")

        boundary = states_gdf[states_gdf[name_col].astype(str).str.lower() == self.region_name.lower()].copy()
        if boundary.empty:
            raise RuntimeError(f"State/region '{self.region_name}' polygon not found in Natural Earth dataset.")

        boundary = reproject_gdf(boundary, "EPSG:4326")
        boundary.to_file(cache_path, driver="GeoJSON")
        logger.info(f"Successfully cached '{self.region_name}' boundary GeoJSON to {cache_path}")

        return boundary
