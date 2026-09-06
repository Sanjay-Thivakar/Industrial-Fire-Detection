"""Sentinel-2 spectral feature extraction engine.

Extracts optical surface reflectance statistics and spectral indices (NDVI, NBR, NDWI, SWIR ratio)
from localized Sentinel-2 Level-2A patches masked strictly by Scene Classification Layer (SCL) quality rules.

IMPORTANT SCIENTIFIC AND DOMAIN CONSTRAINTS:
1. Sentinel-2 is an optical multispectral sensor (VNIR/SWIR), NOT a thermal sensor.
   These features represent optical surface condition (vegetation vigor, moisture, ground surface reflectance).
   They do NOT directly measure thermal plumes or combustion temperatures.
2. SCL Masking Rule:
   Only pixels classified as reliable valid surface (SCL 4 = Vegetation, SCL 5 = Not Vegetated, SCL 6 = Water)
   are used for spectral feature computation.
   SCL 0 (NoData), 1 (Saturated/Defective), 2 (Dark Area), 3 (Cloud Shadow), 7 (Unclassified),
   8 (Cloud Med Prob), 9 (Cloud High Prob), 10 (Thin Cirrus), 11 (Snow/Ice) are strictly excluded.
3. SWIR Ratio (B12 / B11) is an experimental spectral feature retained for later empirical evaluation,
   not an established fire-detection metric.
4. All generated features are strictly prefixed with `s2_`.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# Required bands for Sentinel-2 spectral feature extraction
REQUIRED_BANDS = ("SCL", "B04", "B08", "B11", "B12")

# SCL classes accepted as reliable valid surface
VALID_SURFACE_SCL_CLASSES = {4, 5, 6}


class Sentinel2SpectralExtractor:
    """Extracts optical spectral features and indices from localized Sentinel-2 patches."""

    def __init__(
        self,
        min_valid_pixels: int = 1,
        epsilon: float = 1e-6,
    ):
        """Initialize the spectral extractor.

        Args:
            min_valid_pixels: Minimum number of valid surface pixels required to compute statistics.
            epsilon: Small constant to avoid zero-division in normalized difference indices.
        """
        self.min_valid_pixels = min_valid_pixels
        self.epsilon = epsilon

    @staticmethod
    def _safe_divide(
        numerator: np.ndarray,
        denominator: np.ndarray,
        epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Perform element-wise division safely, setting zero/near-zero denominators to NaN."""
        result = np.full(numerator.shape, np.nan, dtype=np.float64)
        valid = np.isfinite(numerator) & np.isfinite(denominator) & (np.abs(denominator) > epsilon)
        result[valid] = numerator[valid] / denominator[valid]
        return result

    @staticmethod
    def compute_summary_stats(
        values: np.ndarray,
        prefix: str,
    ) -> Dict[str, Union[float, int]]:
        """Compute mean, median, std, min, max, and valid_count for a 1D array of values."""
        clean = values[np.isfinite(values)]
        n = int(clean.size)

        if n == 0:
            return {
                f"{prefix}_mean": np.nan,
                f"{prefix}_median": np.nan,
                f"{prefix}_std": np.nan,
                f"{prefix}_min": np.nan,
                f"{prefix}_max": np.nan,
                f"{prefix}_valid_count": 0,
            }

        return {
            f"{prefix}_mean": float(np.mean(clean)),
            f"{prefix}_median": float(np.median(clean)),
            f"{prefix}_std": float(np.std(clean)),
            f"{prefix}_min": float(np.min(clean)),
            f"{prefix}_max": float(np.max(clean)),
            f"{prefix}_valid_count": n,
        }

    @staticmethod
    def compute_band_stats(
        values: np.ndarray,
        prefix: str,
    ) -> Dict[str, float]:
        """Compute mean, median, and std for raw spectral band reflectance."""
        clean = values[np.isfinite(values)]
        if clean.size == 0:
            return {
                f"{prefix}_mean": np.nan,
                f"{prefix}_median": np.nan,
                f"{prefix}_std": np.nan,
            }
        return {
            f"{prefix}_mean": float(np.mean(clean)),
            f"{prefix}_median": float(np.median(clean)),
            f"{prefix}_std": float(np.std(clean)),
        }

    def _build_empty_feature_dict(
        self,
        total_pixels: int,
        status: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Construct standard feature dictionary with NaN values for failure/empty cases."""
        stats = {
            # Quality & Status metadata
            "s2_total_pixels": total_pixels,
            "s2_spectral_valid_pixels": 0,
            "s2_spectral_valid_pct": 0.0,
            "s2_feature_status": status,
            "s2_feature_failure_reason": reason,
        }

        # Indices NaN
        for idx in ("s2_ndvi", "s2_nbr", "s2_ndwi", "s2_swir_ratio"):
            stats.update({
                f"{idx}_mean": np.nan,
                f"{idx}_median": np.nan,
                f"{idx}_std": np.nan,
                f"{idx}_min": np.nan,
                f"{idx}_max": np.nan,
                f"{idx}_valid_count": 0,
            })

        # Bands NaN
        for band in ("s2_b04", "s2_b08", "s2_b11", "s2_b12"):
            stats.update({
                f"{band}_mean": np.nan,
                f"{band}_median": np.nan,
                f"{band}_std": np.nan,
            })

        return stats

    def extract_features(
        self,
        bands_dict: Dict[str, np.ndarray],
    ) -> Dict[str, Any]:
        """Extract patch-level spectral indices and band statistics from localized patch bands.

        Args:
            bands_dict: Dictionary mapping band names ('SCL', 'B04', 'B08', 'B11', 'B12')
                        to 2D numpy arrays.

        Returns:
            Dictionary containing all extracted features with 's2_' prefix.
        """
        # 1. Check for required bands
        missing = [b for b in REQUIRED_BANDS if b not in bands_dict or bands_dict[b] is None]
        if missing:
            return self._build_empty_feature_dict(
                total_pixels=0,
                status="MISSING_BAND",
                reason=f"Missing required band(s): {', '.join(missing)}",
            )

        # 2. Check dimensions consistency
        shapes = {b: bands_dict[b].shape for b in REQUIRED_BANDS}
        unique_shapes = set(shapes.values())
        if len(unique_shapes) > 1:
            shape_desc = ", ".join([f"{b}: {s}" for b, s in shapes.items()])
            return self._build_empty_feature_dict(
                total_pixels=0,
                status="DIMENSION_MISMATCH",
                reason=f"Mismatched raster dimensions across bands: {shape_desc}",
            )

        sample_shape = next(iter(unique_shapes))
        if len(sample_shape) != 2 or sample_shape[0] == 0 or sample_shape[1] == 0:
            return self._build_empty_feature_dict(
                total_pixels=0,
                status="EMPTY_PATCH",
                reason=f"Patch shape {sample_shape} is empty or non-2D",
            )

        total_pixels = int(sample_shape[0] * sample_shape[1])

        # 3. Extract and cast bands to float64
        scl = np.asarray(bands_dict["SCL"])
        b04 = np.asarray(bands_dict["B04"], dtype=np.float64)
        b08 = np.asarray(bands_dict["B08"], dtype=np.float64)
        b11 = np.asarray(bands_dict["B11"], dtype=np.float64)
        b12 = np.asarray(bands_dict["B12"], dtype=np.float64)

        # 4. Construct SCL valid surface mask
        # Strictly valid: SCL 4 (Vegetation), 5 (Not Vegetated), 6 (Water)
        # Excludes 0, 1, 2, 3, 7, 8, 9, 10, 11
        scl_valid_mask = np.isin(scl, list(VALID_SURFACE_SCL_CLASSES))
        
        # Finite numerical values across all required bands
        finite_mask = (
            np.isfinite(b04) &
            np.isfinite(b08) &
            np.isfinite(b11) &
            np.isfinite(b12)
        )

        valid_mask = scl_valid_mask & finite_mask
        valid_pixel_count = int(np.sum(valid_mask))
        valid_pixel_pct = round((valid_pixel_count / total_pixels) * 100.0, 2)

        if valid_pixel_count < self.min_valid_pixels:
            return self._build_empty_feature_dict(
                total_pixels=total_pixels,
                status="ALL_PIXELS_MASKED",
                reason=f"No reliable valid surface pixels found (0 of {total_pixels} valid)",
            )

        # 5. Extract masked 1D valid arrays for calculation
        b04_valid = b04[valid_mask]
        b08_valid = b08[valid_mask]
        b11_valid = b11[valid_mask]
        b12_valid = b12[valid_mask]

        # 6. Calculate pixel-level spectral indices
        # NDVI = (B08 - B04) / (B08 + B04)
        ndvi_valid = self._safe_divide(b08_valid - b04_valid, b08_valid + b04_valid, self.epsilon)

        # NBR = (B08 - B12) / (B08 + B12)
        nbr_valid = self._safe_divide(b08_valid - b12_valid, b08_valid + b12_valid, self.epsilon)

        # NDWI = (B08 - B11) / (B08 + B11)
        ndwi_valid = self._safe_divide(b08_valid - b11_valid, b08_valid + b11_valid, self.epsilon)

        # SWIR Ratio = B12 / B11 (experimental feature retained for later empirical evaluation)
        swir_ratio_valid = self._safe_divide(b12_valid, b11_valid, self.epsilon)

        # 7. Compute summary statistics for indices
        features: Dict[str, Any] = {
            "s2_total_pixels": total_pixels,
            "s2_spectral_valid_pixels": valid_pixel_count,
            "s2_spectral_valid_pct": valid_pixel_pct,
            "s2_feature_status": "SUCCESS",
            "s2_feature_failure_reason": "",
        }

        features.update(self.compute_summary_stats(ndvi_valid, "s2_ndvi"))
        features.update(self.compute_summary_stats(nbr_valid, "s2_nbr"))
        features.update(self.compute_summary_stats(ndwi_valid, "s2_ndwi"))
        features.update(self.compute_summary_stats(swir_ratio_valid, "s2_swir_ratio"))

        # 8. Compute summary statistics for raw bands
        features.update(self.compute_band_stats(b04_valid, "s2_b04"))
        features.update(self.compute_band_stats(b08_valid, "s2_b08"))
        features.update(self.compute_band_stats(b11_valid, "s2_b11"))
        features.update(self.compute_band_stats(b12_valid, "s2_b12"))

        return features
