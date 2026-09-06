import argparse
from pathlib import Path
from src.config import Config
from src.utils.logger import setup_logger
from src.utils.geo_utils import filter_points_by_boundary
from src.data_ingestion.firms_loader import FirmsLoader
from src.data_ingestion.boundary_loader import BoundaryLoader
from src.data_ingestion.osm_retriever import OsmRetriever
from src.feature_engineering.spatial_features import compute_spatial_features
from src.feature_engineering.temporal_features import compute_temporal_features
from src.feature_engineering.thermal_features import compute_thermal_features
from src.feature_engineering.landcover_sampler import sample_landcover
from src.labeling.weak_labeler import generate_weak_labels
from src.models.train_baseline import train_baseline_rf
from src.visualization.map_builder import build_and_export_results

logger = setup_logger("IndustrialFirePipeline")


def run_pipeline(config_path: str = None, custom_firms_zip: str = None):
    """Executes the full Baseline V1 Industrial Fire AI Pipeline."""
    logger.info("Starting Baseline V1 Industrial Fire AI Pipeline...")
    config = Config.load(config_path)

    # 1. Ingest & Clean FIRMS Data
    firms_loader = FirmsLoader(config)
    firms_zip_path = Path(custom_firms_zip) if custom_firms_zip else None
    firms_df = firms_loader.load_and_clean_firms(custom_zip_path=firms_zip_path)

    # 2. Load State Boundary Polygon
    boundary_loader = BoundaryLoader(config)
    boundary_gdf = boundary_loader.load_boundary()

    # 3. Filter FIRMS Points to State Polygon
    filtered_fires, bbox = filter_points_by_boundary(firms_df, boundary_gdf)
    logger.info(f"Fires inside target state polygon ({config.region.get('name')}): {len(filtered_fires):,}")

    if filtered_fires.empty:
        raise RuntimeError("No FIRMS fire detections found inside the target state boundary.")

    # 4. Retrieve OSM Industrial Facilities
    osm_retriever = OsmRetriever(config)
    osm_df = osm_retriever.retrieve_facilities(bbox)

    # 5. Spatial Feature Engineering (Nearest Facility Matching)
    spatial_df = compute_spatial_features(filtered_fires, osm_df, config)

    # 6. Temporal & Diurnal Feature Engineering
    temporal_df = compute_temporal_features(spatial_df, config)

    # 7. Thermal & Local Grid Persistence Feature Engineering
    thermal_df = compute_thermal_features(temporal_df, config)

    # 8. ESA WorldCover Land Cover Sampling
    features_df = sample_landcover(thermal_df, config)

    # 9. Weak Label Generation
    labeled_df = generate_weak_labels(features_df, config)

    # 10. Baseline Random Forest Model Training
    clf, classified_df, importances = train_baseline_rf(labeled_df, config)

    # 11. Export Results & Build Interactive HTML GIS Map
    build_and_export_results(classified_df, osm_df, boundary_gdf, config)

    logger.info("=" * 60)
    logger.info("BASELINE V1 PIPELINE EXECUTED SUCCESSFULLY")
    logger.info(f"Classified detections: {len(classified_df):,}")
    logger.info(f"Predicted class breakdown:\n{classified_df['predicted_class'].value_counts()}")
    logger.info("=" * 60)

    return classified_df
