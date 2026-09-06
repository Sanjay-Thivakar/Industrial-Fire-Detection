import zipfile
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("FirmsLoader")

# Default Tamil Nadu bounding box as geographic pre-filter safety net [minx, miny, maxx, maxy]
DEFAULT_TN_BBOX = (76.23, 8.08, 80.35, 13.54)


class FirmsLoader:
    """
    Ingests and cleans NASA FIRMS thermal anomaly data from multi-GB CSV files or ZIP archives
    using memory-safe chunked streaming ingestion and geographic bounding-box pre-filtering.
    """

    def __init__(self, config: Config):
        self.config = config
        self.raw_dir = config.raw_dir
        self.cache_dir = config.cache_dir
        self.chunk_size = config.firms.get("chunk_size", 100000)

    def locate_firms_files(self, custom_zip_path: Optional[Path] = None) -> List[Path]:
        """
        Locates NASA FIRMS CSV files across `data/raw/firms/`, `data/raw/`,
        or extracts a ZIP archive if provided or found.
        """
        found_csvs: List[Path] = []

        # 1. Search raw_dir/firms subdirectories (e.g. firms/viirs_noaa20/, firms/viirs_snpp/, firms/modis/)
        firms_subdir = self.raw_dir / "firms"
        if firms_subdir.exists():
            subdir_csvs = list(firms_subdir.rglob("*.csv"))
            if subdir_csvs:
                logger.info(f"Found {len(subdir_csvs)} FIRMS CSV files under {firms_subdir}")
                found_csvs.extend(subdir_csvs)

        # 2. Search root raw_dir for standalone CSV files
        root_raw_csvs = list(self.raw_dir.glob("*.csv"))
        for c in root_raw_csvs:
            if c not in found_csvs:
                found_csvs.append(c)

        if found_csvs:
            return found_csvs

        # 3. If no direct CSV files found, check for ZIP archive
        extract_dir = self.cache_dir / "firms_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        cached_csvs = list(extract_dir.rglob("*.csv"))

        if cached_csvs:
            logger.info(f"Found {len(cached_csvs)} cached extracted CSV files in {extract_dir}")
            return cached_csvs

        zip_path = custom_zip_path or self.config.firms_zip
        if zip_path is None or not zip_path.exists():
            zip_files = list(self.raw_dir.glob("*.zip"))
            if not zip_files:
                zip_files = list(self.config.project_root.glob("*.zip"))
            if not zip_files:
                raise FileNotFoundError(
                    f"No FIRMS CSV files or ZIP archives found in raw_dir ({self.raw_dir}) or project root."
                )
            preferred = [z for z in zip_files if "archive" in z.name.lower() or "firms" in z.name.lower()]
            zip_path = preferred[0] if preferred else max(zip_files, key=lambda x: x.stat().st_size)

        logger.info(f"Extracting FIRMS ZIP archive: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        extracted_csvs = list(extract_dir.rglob("*.csv"))
        logger.info(f"Extraction complete. Found {len(extracted_csvs)} CSV files.")
        return extracted_csvs

    def load_and_clean_firms(
        self,
        custom_zip_path: Optional[Path] = None,
        target_bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> pd.DataFrame:
        """
        Loads configured FIRMS datasets using chunked streaming, validates coordinates,
        pre-filters by geographic bounding box, and returns candidate records.
        """
        cache_file = self.cache_dir / "VIIRS_primary_clean.csv"
        if cache_file.exists():
            logger.info(f"Loading cached cleaned FIRMS dataset: {cache_file}")
            df = pd.read_csv(cache_file, low_memory=False)
            df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
            return df

        csv_files = self.locate_firms_files(custom_zip_path)
        logger.info(f"Located {len(csv_files)} total candidate CSV file(s).")

        primary_sensors = self.config.firms.get("primary_sensors", [])
        extensible_sensors = self.config.firms.get("extensible_sensors", [])

        # Build list of active configured sensor targets
        active_sensors = []
        for sensor_info in primary_sensors:
            active_sensors.append((sensor_info["name"], sensor_info["pattern"], True))

        for sensor_info in extensible_sensors:
            include = sensor_info.get("include_in_baseline", False)
            active_sensors.append((sensor_info["name"], sensor_info["pattern"], include))

        # Geographic bounding box filter parameters
        bbox = target_bbox or DEFAULT_TN_BBOX
        minx, miny, maxx, maxy = bbox
        logger.info(
            f"Applying geographic pre-filter bbox: lon [{minx:.2f}, {maxx:.2f}], lat [{miny:.2f}, {maxy:.2f}] "
            f"with chunk size {self.chunk_size:,}"
        )

        # Ingestion Statistics Counters
        stats = {
            "files_processed": 0,
            "chunks_processed": 0,
            "total_source_rows": 0,
            "coord_valid_rows": 0,
            "bbox_surviving_rows": 0,
            "sensor_counts": {},
        }

        candidate_chunks: List[pd.DataFrame] = []

        for name, pattern, enabled in active_sensors:
            stats["sensor_counts"][name] = 0
            if not enabled:
                logger.info(f"Sensor '{name}' is disabled in configuration. Skipping pattern '{pattern}'.")
                continue

            matched_files = [f for f in csv_files if pattern.upper() in f.name.upper()]
            if not matched_files:
                logger.warning(f"No CSV files matched pattern '{pattern}' for sensor '{name}'.")
                continue

            for file_path in matched_files:
                logger.info(f"Streaming ingestion for sensor '{name}' from: {file_path.name}")
                stats["files_processed"] += 1

                try:
                    reader = pd.read_csv(file_path, chunksize=self.chunk_size, low_memory=False)
                    for chunk in reader:
                        stats["chunks_processed"] += 1
                        stats["total_source_rows"] += len(chunk)

                        # 1. Required column validation
                        required = ["latitude", "longitude", "brightness", "frp", "acq_date"]
                        if not all(col in chunk.columns for col in required):
                            logger.warning(f"Chunk missing required columns in {file_path.name}. Skipping chunk.")
                            continue

                        # 2. Coerce numeric types & clean invalid coordinates
                        numeric_cols = ["latitude", "longitude", "brightness", "scan", "track", "bright_t31", "frp"]
                        for col in numeric_cols:
                            if col in chunk.columns:
                                chunk[col] = pd.to_numeric(chunk[col], errors="coerce")

                        clean_chunk = chunk[
                            chunk["latitude"].between(-90, 90) & chunk["longitude"].between(-180, 180)
                        ].dropna(subset=["latitude", "longitude", "acq_date", "brightness", "frp"])

                        stats["coord_valid_rows"] += len(clean_chunk)

                        # 3. Geographic bounding-box pre-filtering
                        bbox_mask = (
                            clean_chunk["longitude"].between(minx, maxx)
                            & clean_chunk["latitude"].between(miny, maxy)
                        )
                        filtered_chunk = clean_chunk[bbox_mask].copy()

                        if not filtered_chunk.empty:
                            filtered_chunk["satellite_source"] = name
                            stats["bbox_surviving_rows"] += len(filtered_chunk)
                            stats["sensor_counts"][name] += len(filtered_chunk)
                            candidate_chunks.append(filtered_chunk)

                except Exception as e:
                    logger.error(f"Error streaming file {file_path.name}: {e}")

        if not candidate_chunks:
            raise RuntimeError(
                f"Zero FIRMS records survived ingestion and bbox filtering across all {stats['files_processed']} processed files."
            )

        df = pd.concat(candidate_chunks, ignore_index=True)
        df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
        df = df.drop_duplicates().reset_index(drop=True)

        logger.info("=" * 60)
        logger.info("FIRMS INGESTION SUMMARY STATISTICS:")
        logger.info(f"  Files processed: {stats['files_processed']}")
        logger.info(f"  Chunks processed: {stats['chunks_processed']}")
        logger.info(f"  Total source rows: {stats['total_source_rows']:,}")
        logger.info(f"  Rows surviving coordinate validation: {stats['coord_valid_rows']:,}")
        logger.info(f"  Rows surviving bbox pre-filter: {stats['bbox_surviving_rows']:,}")
        logger.info(f"  Final candidate rows (after deduplication): {len(df):,}")
        logger.info(f"  Sensor breakdown: {stats['sensor_counts']}")
        logger.info("=" * 60)

        df.to_csv(cache_file, index=False)
        logger.info(f"Saved cleaned candidate FIRMS dataset to cache: {cache_file}")

        return df
