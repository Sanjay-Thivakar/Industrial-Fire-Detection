import folium
import numpy as np
import pandas as pd
import geopandas as gpd
from folium.plugins import MarkerCluster
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("MapBuilder")

CLASS_COLORS = {
    "Persistent Thermal Source": "orange",
    "Industrial Fire": "red",
    "Forest Fire": "darkgreen",
    "Agricultural Burning": "goldenrod",
    "Possible Forest Fire": "green",
    "Possible Agricultural Burning": "khaki",
    "Other/Unclassified": "gray",
}


def build_and_export_results(
    features_df: pd.DataFrame,
    osm_df: pd.DataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    config: Config
) -> None:
    """Exports classified CSV, GeoJSON, and interactive HTML Folium GIS map."""
    logger.info("Exporting classified results and building interactive GIS map...")
    out_dir = config.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    features_out = features_df.replace([np.inf, -np.inf], np.nan)

    # 1. Export CSV
    csv_filename = config.outputs.get("csv_file", "TamilNadu_Classified_Fires.csv")
    csv_path = out_dir / csv_filename
    features_out.to_csv(csv_path, index=False)
    logger.info(f"Saved classified CSV to: {csv_path}")

    # 2. Export GeoJSON
    geo_out = gpd.GeoDataFrame(
        features_out,
        geometry=gpd.points_from_xy(features_out["longitude"], features_out["latitude"]),
        crs="EPSG:4326",
    )
    geojson_filename = config.outputs.get("geojson_file", "TamilNadu_Classified_Fires.geojson")
    geojson_path = out_dir / geojson_filename
    geo_out.to_file(geojson_path, driver="GeoJSON")
    logger.info(f"Saved classified GeoJSON to: {geojson_path}")

    # 3. Interactive Folium HTML Map
    map_filename = config.outputs.get("html_map_file", "TamilNadu_FireMap.html")
    map_path = out_dir / map_filename

    center_lat = features_out["latitude"].mean()
    center_lon = features_out["longitude"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles="CartoDB positron",
    )

    # Classified Fire Layers
    unique_classes = features_out["predicted_class"].unique()
    fire_layers = {cls: folium.FeatureGroup(name=f"Fires: {cls}") for cls in unique_classes}

    for _, row in features_out.iterrows():
        cls = row["predicted_class"]
        color = CLASS_COLORS.get(cls, "black")
        
        dist_km = row.get('distance_to_facility_km', 0.0)
        dist_str = f"{dist_km:.2f} km" if pd.notna(dist_km) else "N/A"
        conf = row.get('predicted_class_confidence', 0.0)
        conf_str = f"{conf:.2f}" if pd.notna(conf) else "N/A"

        popup_html = (
            f"<b>{cls}</b><br>"
            f"Date: {row.get('acq_date')}<br>"
            f"FRP: {row.get('frp')}<br>"
            f"Brightness: {row.get('brightness')}<br>"
            f"Land cover: {row.get('landcover_class', 'N/A')}<br>"
            f"Nearest facility: {row.get('name', 'N/A')} ({row.get('facility_type', 'N/A')})<br>"
            f"Distance: {dist_str}<br>"
            f"Confidence: {conf_str}"
        )

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(fire_layers[cls])

    for layer in fire_layers.values():
        layer.add_to(m)

    # OSM Facility Layer
    if not osm_df.empty:
        facility_layer = folium.FeatureGroup(name="OSM Industrial Facilities")
        facility_cluster = MarkerCluster().add_to(facility_layer)
        for _, row in osm_df.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                icon=folium.Icon(color="blue", icon="industry", prefix="fa"),
                popup=f"{row.get('name', 'Unnamed')} ({row.get('facility_type')})",
            ).add_to(facility_cluster)
        facility_layer.add_to(m)

    # State Boundary Polygon Layer
    if not boundary_gdf.empty:
        folium.GeoJson(
            boundary_gdf.to_json(),
            name=f"{config.region.get('name', 'State')} Boundary",
            style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 2},
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(map_path))
    logger.info(f"Saved interactive HTML map to: {map_path}")
