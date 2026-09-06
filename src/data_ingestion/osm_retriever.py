"""
OsmRetriever — Phase 2C tiled implementation.

Strategy
--------
Divides Tamil Nadu into a 5×5 geographic grid (25 tiles) and issues a
separate Overpass QL query per tile.  This avoids server-side timeout and
payload truncation that affected the original single-query approach.

Key design decisions
--------------------
* OSM object identity is preserved via (osm_type, osm_id). Two distinct OSM
  objects are never merged even if they are spatially adjacent.
* Mirror failover: tries overpass-api.de → kumi.systems → openstreetmap.ru →
  private.coffee, each mirror up to max_retries attempts.
* A failed tile is recorded as success=False and skipped (pipeline continues).
* Facility classification uses a 3-tier relevance hierarchy:
    HIGHER_RELEVANCE  — refineries, power plants, steel, cement, mining,
                        oil/gas/chemicals, industrial works
    GENERAL_CONTEXT   — generic industrial landuse/buildings
    CAUTION_LOWER_RELEVANCE — substations, warehouses/depots

  A power substation or generic building=industrial is NOT treated as a
  thermal-emitting facility.
"""

import json
import time
import numpy as np
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("OsmRetriever")

# Tamil Nadu bounding box (south, west, north, east)
TN_BBOX = (8.08, 76.23, 13.54, 80.35)

# Number of tiles along each axis  →  5 × 5 = 25 tiles
N_LAT_TILES = 5
N_LON_TILES = 5

# Small overlap to avoid missing features on tile boundaries
TILE_OVERLAP_DEG = 0.01


def classify_osm_element(tags: dict) -> dict:
    """
    Assigns a normalized_category, relevance_tier, and facility_type to an
    OSM element based on its tags.

    Tiers
    -----
    HIGHER_RELEVANCE       — facilities with direct thermal-emission potential
                             (refineries, power plants, steel, cement, mining,
                             oil/gas/chemicals, large industrial works).
    GENERAL_CONTEXT        — industrial landuse zones and generic industrial
                             buildings.  Useful context but NOT proof of a
                             thermal anomaly source.
    CAUTION_LOWER_RELEVANCE — substations, warehouses, depots.  Present in
                             industrial areas but carry little direct thermal
                             relevance.
    """
    power = str(tags.get("power", "")).lower()
    industrial = str(tags.get("industrial", "")).lower()
    man_made = str(tags.get("man_made", "")).lower()
    landuse = str(tags.get("landuse", "")).lower()
    building = str(tags.get("building", "")).lower()
    name = str(tags.get("name", "")).lower()

    # ── 1. Refinery / Petrochemical ──────────────────────────────────────────
    if (
        man_made in ("refinery", "petroleum_refinery")
        or industrial in ("refinery", "petrochemical", "petroleum")
        or "refinery" in name
        or "petrochemical" in name
    ):
        return {
            "normalized_category": "Refinery / Petrochemical",
            "relevance_tier": "HIGHER_RELEVANCE",
            "facility_type": "Oil & Gas",
        }

    # ── 2. Power Plant ────────────────────────────────────────────────────────
    if (
        power in ("plant", "generator")
        or industrial in ("power", "power_plant")
        or "power station" in name
        or "thermal power" in name
        or "power plant" in name
    ):
        return {
            "normalized_category": "Power Plant",
            "relevance_tier": "HIGHER_RELEVANCE",
            "facility_type": "Power Plant",
        }

    # ── 3. Substation — CAUTION: low direct thermal relevance ─────────────────
    if power == "substation" or industrial == "substation":
        return {
            "normalized_category": "Substation & Electrical Infrastructure",
            "relevance_tier": "CAUTION_LOWER_RELEVANCE",
            "facility_type": "Other Industrial",
        }

    # ── 4. Steel / Metallurgy ─────────────────────────────────────────────────
    if (
        industrial in ("steel", "metallurgy", "smelter", "foundry", "metal")
        or "steel" in name
        or "iron" in name
        or "metallurgy" in name
        or "smelter" in name
        or "foundry" in name
    ):
        return {
            "normalized_category": "Steel / Metallurgy",
            "relevance_tier": "HIGHER_RELEVANCE",
            "facility_type": "Manufacturing",
        }

    # ── 5. Cement & Construction Materials ────────────────────────────────────
    if (
        industrial in ("cement", "bricks", "lime", "concrete", "construction_materials")
        or "cement" in name
        or "clinker" in name
    ):
        return {
            "normalized_category": "Cement & Construction Materials",
            "relevance_tier": "HIGHER_RELEVANCE",
            "facility_type": "Construction Materials",
        }

    # ── 6. Mining & Quarry ────────────────────────────────────────────────────
    if (
        industrial in ("mine", "mining", "quarry")
        or landuse == "quarry"
        or "quarry" in name
        or "mine" in name
    ):
        return {
            "normalized_category": "Mining & Quarry",
            "relevance_tier": "HIGHER_RELEVANCE",
            "facility_type": "Mining",
        }

    # ── 7. Oil, Gas & Chemical ────────────────────────────────────────────────
    if (
        industrial in ("oil", "gas", "chemical", "chemicals", "petroleum", "fertilizer", "lng", "lpg")
        or "chemical" in name
        or "fertilizer" in name
        or " lpg " in name
        or " lng " in name
        or "petrochemical" in name
    ):
        return {
            "normalized_category": "Oil, Gas & Chemical",
            "relevance_tier": "HIGHER_RELEVANCE",
            "facility_type": "Chemical",
        }

    # ── 8. Manufacturing & Industrial Works ───────────────────────────────────
    if (
        man_made == "works"
        or industrial in ("factory", "manufacture", "manufacturing", "works")
        or "works" in name
        or "factory" in name
    ):
        return {
            "normalized_category": "Manufacturing & Industrial Works",
            "relevance_tier": "HIGHER_RELEVANCE",
            "facility_type": "Industrial Works",
        }

    # ── 9. Warehouse & Logistics — CAUTION ────────────────────────────────────
    if (
        industrial in ("warehouse", "depot", "logistics")
        or "warehouse" in name
        or "depot" in name
    ):
        return {
            "normalized_category": "Warehouse & Logistics",
            "relevance_tier": "CAUTION_LOWER_RELEVANCE",
            "facility_type": "Warehouse/Depot",
        }

    # ── 10. Industrial Area / Zone ────────────────────────────────────────────
    if landuse == "industrial" or industrial in (
        "industrial_estate", "industrial_park", "industrial_zone", "area"
    ):
        return {
            "normalized_category": "Industrial Area / Zone",
            "relevance_tier": "GENERAL_CONTEXT",
            "facility_type": "Other Industrial",
        }

    # ── 11. Generic Industrial Building ──────────────────────────────────────
    if building == "industrial":
        return {
            "normalized_category": "Generic Industrial Building",
            "relevance_tier": "GENERAL_CONTEXT",
            "facility_type": "Other Industrial",
        }

    # ── Default ───────────────────────────────────────────────────────────────
    return {
        "normalized_category": "Other Industrial",
        "relevance_tier": "GENERAL_CONTEXT",
        "facility_type": "Other Industrial",
    }


class OsmRetriever:
    """
    Queries Overpass API via a tiled 5×5 geographic grid over Tamil Nadu.

    Each tile is queried independently with retry/mirror failover.
    OSM object identity (osm_type, osm_id) is preserved through deduplication.
    """

    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.cache_dir
        self.output_dir = config.output_dir
        self.mirrors: List[str] = config.osm.get(
            "overpass_mirrors",
            [
                "https://overpass-api.de/api/interpreter",
                "https://overpass.kumi.systems/api/interpreter",
                "https://overpass.openstreetmap.ru/api/interpreter",
                "https://overpass.private.coffee/api/interpreter",
            ],
        )
        self.timeout: int = config.osm.get("timeout_seconds", 60)
        self.max_retries: int = config.osm.get("max_retries", 2)
        self.cache_json = self.cache_dir / config.osm.get(
            "cache_json", "osm_industrial_facilities.json"
        )
        self.output_csv = self.output_dir / config.osm.get(
            "output_csv", "OSM_Industrial_Facilities.csv"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def retrieve_facilities(
        self, bbox: Tuple[float, float, float, float]
    ) -> pd.DataFrame:
        """
        Retrieve OSM industrial facilities within *bbox* = (minx, miny, maxx, maxy).

        If a valid cached JSON exists (containing metadata confirming a tiled
        retrieval), it is used directly.  Otherwise a fresh 25-tile retrieval
        is performed.

        Returns
        -------
        pd.DataFrame with columns:
            osm_id, osm_type, latitude, longitude, name, operator,
            normalized_category, relevance_tier, facility_type,
            source_tile, raw_tags
        """
        minx, miny, maxx, maxy = bbox

        if self.cache_json.exists():
            with open(self.cache_json, "r", encoding="utf-8") as f:
                cached = json.load(f)
            # Accept only caches produced by the tiled retriever
            if cached.get("retrieval_strategy") == "tiled_25":
                logger.info(
                    f"Loading cached 25-tile OSM facilities from: {self.cache_json}"
                )
                elements = cached.get("elements", [])
                tile_report = cached.get("tile_report", [])
                return self._parse_and_save(elements, tile_report)
            else:
                logger.warning(
                    "Cached OSM data is from an older single-query retrieval. "
                    "Re-running tiled retrieval."
                )

        logger.info(
            f"Executing 25-tile Overpass retrieval over bbox "
            f"[{miny:.2f}, {minx:.2f}, {maxy:.2f}, {maxx:.2f}]..."
        )
        elements, tile_report = self._run_tiled_retrieval(miny, minx, maxy, maxx)

        # Cache raw results
        cache_data = {
            "retrieval_strategy": "tiled_25",
            "retrieval_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "bounding_box": [miny, minx, maxy, maxx],
            "n_lat_tiles": N_LAT_TILES,
            "n_lon_tiles": N_LON_TILES,
            "total_raw_elements": sum(
                r.get("retrieved_count", 0) for r in tile_report
            ),
            "tile_report": tile_report,
            "elements": elements,
        }
        self.cache_json.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_json, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        logger.info(f"Cached raw OSM data to {self.cache_json}")

        return self._parse_and_save(elements, tile_report)

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _build_tile_query(self, ts: float, tw: float, tn: float, te: float) -> str:
        """Build an Overpass QL query for one tile."""
        bbox_str = f"{ts:.3f},{tw:.3f},{tn:.3f},{te:.3f}"
        return (
            f"[out:json][timeout:{self.timeout}];\n"
            "(\n"
            f'  nwr["landuse"="industrial"]({bbox_str});\n'
            f'  nwr["landuse"="quarry"]({bbox_str});\n'
            f'  nwr["industrial"]({bbox_str});\n'
            f'  nwr["man_made"="refinery"]({bbox_str});\n'
            f'  nwr["man_made"="petroleum_refinery"]({bbox_str});\n'
            f'  nwr["man_made"="works"]({bbox_str});\n'
            f'  nwr["power"="plant"]({bbox_str});\n'
            f'  nwr["power"="generator"]({bbox_str});\n'
            f'  nwr["power"="substation"]({bbox_str});\n'
            f'  nwr["building"="industrial"]({bbox_str});\n'
            ");\n"
            "out center qt;"
        )

    def _query_tile(self, tile_id: str, query: str) -> Optional[List[dict]]:
        """
        Try each mirror up to max_retries times.  Returns element list on
        success, None if all mirrors fail.
        """
        headers = {"User-Agent": "IndustrialFireAI/1.0 (SIH research project)"}
        for mirror in self.mirrors:
            for attempt in range(1, self.max_retries + 1):
                logger.info(
                    f"Querying tile {tile_id} on {mirror} (attempt {attempt})..."
                )
                try:
                    resp = requests.get(
                        mirror,
                        params={"data": query},
                        headers=headers,
                        timeout=self.timeout + 15,
                    )
                    if resp.status_code == 200:
                        elements = resp.json().get("elements", [])
                        return elements
                    else:
                        logger.warning(
                            f"  HTTP {resp.status_code} from {mirror} "
                            f"for tile {tile_id}"
                        )
                except Exception as exc:
                    logger.warning(
                        f"  Exception querying {mirror} for tile {tile_id}: {exc}"
                    )
                if attempt < self.max_retries:
                    time.sleep(3)
        return None

    def _run_tiled_retrieval(
        self, south: float, west: float, north: float, east: float
    ) -> Tuple[List[dict], List[dict]]:
        """
        Partition the bounding box into N_LAT_TILES × N_LON_TILES tiles and
        query each independently.  Returns (unique_elements, tile_report).
        """
        lat_edges = np.linspace(south, north, N_LAT_TILES + 1)
        lon_edges = np.linspace(west, east, N_LON_TILES + 1)

        tiles = []
        for i in range(N_LAT_TILES):
            for j in range(N_LON_TILES):
                tiles.append(
                    {
                        "tile_id": f"tile_{i+1}_{j+1}",
                        "bounds": (
                            max(south, lat_edges[i] - TILE_OVERLAP_DEG),
                            max(west, lon_edges[j] - TILE_OVERLAP_DEG),
                            min(north, lat_edges[i + 1] + TILE_OVERLAP_DEG),
                            min(east, lon_edges[j + 1] + TILE_OVERLAP_DEG),
                        ),
                    }
                )

        n_total = len(tiles)
        logger.info(f"Partitioned region into {n_total} geographic retrieval tiles.")

        all_raw: List[dict] = []
        seen_ids: set = set()
        tile_report: List[dict] = []

        for idx, tile in enumerate(tiles):
            t_id = tile["tile_id"]
            ts, tw, tn, te = tile["bounds"]
            query = self._build_tile_query(ts, tw, tn, te)

            result = self._query_tile(t_id, query)

            if result is not None:
                count = len(result)
                for el in result:
                    key = (el.get("type"), el.get("id"))
                    if key not in seen_ids:
                        seen_ids.add(key)
                        el["_source_tile"] = t_id
                        all_raw.append(el)
                tile_report.append(
                    {
                        "tile_id": t_id,
                        "bounds": f"[{ts:.2f},{tw:.2f},{tn:.2f},{te:.2f}]",
                        "success": True,
                        "retrieved_count": count,
                        "error": "",
                    }
                )
                logger.info(
                    f"Tile {idx+1}/{n_total} ({t_id}): success=True, objects={count:,}"
                )
            else:
                tile_report.append(
                    {
                        "tile_id": t_id,
                        "bounds": f"[{ts:.2f},{tw:.2f},{tn:.2f},{te:.2f}]",
                        "success": False,
                        "retrieved_count": 0,
                        "error": "all mirrors exhausted",
                    }
                )
                logger.warning(
                    f"Tile {idx+1}/{n_total} ({t_id}): success=False, "
                    "all mirrors exhausted — tile skipped."
                )

            # Polite delay between tile requests
            time.sleep(1)

        logger.info(
            f"Tiled retrieval complete. "
            f"Successful tiles: {sum(r['success'] for r in tile_report)}/{n_total}. "
            f"Unique raw elements collected: {len(all_raw):,}."
        )
        return all_raw, tile_report

    def _parse_and_save(
        self, elements: List[dict], tile_report: List[dict]
    ) -> pd.DataFrame:
        """
        Parse raw OSM elements into a structured DataFrame, classify each
        element using the 3-tier relevance system, deduplicate by
        (osm_type, osm_id), and save to CSV.
        """
        records = []
        for el in elements:
            tags = el.get("tags", {})
            if el.get("type") == "node":
                lat, lon = el.get("lat"), el.get("lon")
            else:
                center = el.get("center", {})
                lat, lon = center.get("lat"), center.get("lon")

            if lat is None or lon is None:
                continue

            cls = classify_osm_element(tags)
            records.append(
                {
                    "osm_id": el.get("id"),
                    "osm_type": el.get("type"),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "name": str(tags.get("name", "")),
                    "operator": str(tags.get("operator", "")),
                    "normalized_category": cls["normalized_category"],
                    "relevance_tier": cls["relevance_tier"],
                    "facility_type": cls["facility_type"],
                    "source_tile": el.get("_source_tile", ""),
                    "raw_tags": json.dumps(tags),
                }
            )

        osm_df = pd.DataFrame(records)
        if not osm_df.empty:
            osm_df = osm_df.drop_duplicates(
                subset=["osm_type", "osm_id"]
            ).reset_index(drop=True)

        n_success = sum(r.get("success", False) for r in tile_report)
        n_total = len(tile_report)
        logger.info(
            f"Unique OSM industrial facilities parsed: {len(osm_df):,} "
            f"(from {n_success}/{n_total} successful tiles)"
        )
        if not osm_df.empty:
            logger.info(
                "Relevance tier distribution: "
                + str(osm_df["relevance_tier"].value_counts().to_dict())
            )
            logger.info(
                "Category distribution: "
                + str(osm_df["normalized_category"].value_counts().to_dict())
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        osm_df.to_csv(self.output_csv, index=False)
        logger.info(f"Saved OSM industrial facilities CSV to {self.output_csv}")

        return osm_df
