"""Deterministic unit tests for Sentinel-2 spectral feature extraction engine.

All tests use synthetic arrays with ZERO external dependencies.
"""

import numpy as np
import pytest

from src.feature_engineering.sentinel2_spectral import (
    Sentinel2SpectralExtractor,
    REQUIRED_BANDS,
)


class TestSentinel2SpectralExtractor:
    """Tests for Sentinel2SpectralExtractor formulas, SCL masking, and edge case handling."""

    @pytest.fixture
    def extractor(self):
        return Sentinel2SpectralExtractor()

    def test_spectral_indices_exact_values(self, extractor):
        """Verify mathematical calculation of NDVI, NBR, NDWI, and SWIR ratio."""
        # 2x2 uniform patch with valid vegetation SCL=4
        shape = (2, 2)
        bands = {
            "SCL": np.full(shape, 4, dtype=int),
            "B04": np.full(shape, 1000.0),  # Red
            "B08": np.full(shape, 3000.0),  # NIR
            "B11": np.full(shape, 1500.0),  # SWIR-1
            "B12": np.full(shape, 1200.0),  # SWIR-2
        }

        # Expected:
        # NDVI = (3000 - 1000) / (3000 + 1000) = 2000 / 4000 = 0.5
        # NBR = (3000 - 1200) / (3000 + 1200) = 1800 / 4200 = 0.4285714
        # NDWI = (3000 - 1500) / (3000 + 1500) = 1500 / 4500 = 0.3333333
        # SWIR ratio = 1200 / 1500 = 0.8
        features = extractor.extract_features(bands)

        assert features["s2_feature_status"] == "SUCCESS"
        assert features["s2_spectral_valid_pixels"] == 4
        assert features["s2_spectral_valid_pct"] == 100.0

        assert pytest.approx(features["s2_ndvi_mean"], rel=1e-5) == 0.5
        assert pytest.approx(features["s2_ndvi_median"], rel=1e-5) == 0.5
        assert pytest.approx(features["s2_ndvi_std"], abs=1e-5) == 0.0

        assert pytest.approx(features["s2_nbr_mean"], rel=1e-5) == 1800.0 / 4200.0
        assert pytest.approx(features["s2_ndwi_mean"], rel=1e-5) == 1500.0 / 4500.0
        assert pytest.approx(features["s2_swir_ratio_mean"], rel=1e-5) == 0.8

        # Raw band stats
        assert pytest.approx(features["s2_b04_mean"], rel=1e-5) == 1000.0
        assert pytest.approx(features["s2_b08_mean"], rel=1e-5) == 3000.0
        assert pytest.approx(features["s2_b11_mean"], rel=1e-5) == 1500.0
        assert pytest.approx(features["s2_b12_mean"], rel=1e-5) == 1200.0

    def test_scl_masking_strictly_excludes_invalid_classes(self, extractor):
        """Verify that SCL 0, 1, 2, 3, 7, 8, 9, 10, 11 are completely excluded from calculations."""
        # 3x4 patch: 12 pixels total, each with a different SCL class from 0 to 11
        shape = (3, 4)
        scl = np.arange(12, dtype=int).reshape(shape)

        # Assign distinct reflectance per pixel
        b04 = np.full(shape, 1000.0)
        b08 = np.full(shape, 3000.0)
        b11 = np.full(shape, 1500.0)
        b12 = np.full(shape, 1200.0)

        # Poison excluded pixels with extreme values to prove they don't affect statistics
        # E.g., SCL=2 (Dark area) and SCL=7 (Unclassified) have huge values
        b08[scl == 2] = 99999.0
        b08[scl == 7] = 99999.0
        b08[scl == 9] = 99999.0  # Cloud

        bands = {
            "SCL": scl,
            "B04": b04,
            "B08": b08,
            "B11": b11,
            "B12": b12,
        }

        features = extractor.extract_features(bands)

        assert features["s2_feature_status"] == "SUCCESS"
        # Only classes 4 (Veg), 5 (Not Veg), 6 (Water) must be accepted -> exactly 3 pixels
        assert features["s2_spectral_valid_pixels"] == 3
        assert pytest.approx(features["s2_spectral_valid_pct"], rel=1e-3) == (3 / 12) * 100.0

        # Mean NDVI must still be exactly 0.5 because the poison pixels were excluded
        assert pytest.approx(features["s2_ndvi_mean"], rel=1e-5) == 0.5
        assert pytest.approx(features["s2_b08_mean"], rel=1e-5) == 3000.0

    def test_zero_denominator_safe_handling(self, extractor):
        """Verify zero denominator (e.g. 0/0) results in NaN without crashing or warnings."""
        shape = (2, 2)
        bands = {
            "SCL": np.full(shape, 4, dtype=int),
            "B04": np.zeros(shape),
            "B08": np.zeros(shape),
            "B11": np.zeros(shape),
            "B12": np.zeros(shape),
        }

        features = extractor.extract_features(bands)
        assert features["s2_feature_status"] == "SUCCESS"
        assert features["s2_spectral_valid_pixels"] == 4
        # Since 0/0 is invalid, valid_count for NDVI is 0 and mean is NaN
        assert np.isnan(features["s2_ndvi_mean"])
        assert features["s2_ndvi_valid_count"] == 0

    def test_nan_and_inf_handling(self, extractor):
        """Verify NaN or Inf in reflectance arrays are masked out safely."""
        shape = (2, 2)
        b04 = np.array([[1000.0, np.nan], [1000.0, 1000.0]])
        b08 = np.array([[3000.0, 3000.0], [np.inf, 3000.0]])
        bands = {
            "SCL": np.full(shape, 4, dtype=int),
            "B04": b04,
            "B08": b08,
            "B11": np.full(shape, 1500.0),
            "B12": np.full(shape, 1200.0),
        }

        features = extractor.extract_features(bands)
        assert features["s2_feature_status"] == "SUCCESS"
        # 2 pixels had NaN/Inf, so only 2 valid pixels remain
        assert features["s2_spectral_valid_pixels"] == 2
        assert features["s2_spectral_valid_pct"] == 50.0
        assert pytest.approx(features["s2_ndvi_mean"], rel=1e-5) == 0.5

    def test_missing_required_band(self, extractor):
        """Missing required band returns MISSING_BAND status."""
        shape = (2, 2)
        bands = {
            "SCL": np.full(shape, 4, dtype=int),
            "B04": np.full(shape, 1000.0),
            "B08": np.full(shape, 3000.0),
            "B11": np.full(shape, 1500.0),
            # Missing B12
        }

        features = extractor.extract_features(bands)
        assert features["s2_feature_status"] == "MISSING_BAND"
        assert "B12" in features["s2_feature_failure_reason"]
        assert np.isnan(features["s2_ndvi_mean"])

    def test_mismatched_dimensions(self, extractor):
        """Mismatched band dimensions returns DIMENSION_MISMATCH status."""
        bands = {
            "SCL": np.full((10, 10), 4, dtype=int),
            "B04": np.full((10, 10), 1000.0),
            "B08": np.full((10, 10), 3000.0),
            "B11": np.full((20, 20), 1500.0),  # Mismatched
            "B12": np.full((10, 10), 1200.0),
        }

        features = extractor.extract_features(bands)
        assert features["s2_feature_status"] == "DIMENSION_MISMATCH"
        assert "B11" in features["s2_feature_failure_reason"]

    def test_all_pixels_masked(self, extractor):
        """Patch where all pixels are clouds/invalid returns ALL_PIXELS_MASKED status."""
        shape = (5, 5)
        bands = {
            "SCL": np.full(shape, 9, dtype=int),  # 100% Cloud High Probability
            "B04": np.full(shape, 5000.0),
            "B08": np.full(shape, 5000.0),
            "B11": np.full(shape, 5000.0),
            "B12": np.full(shape, 5000.0),
        }

        features = extractor.extract_features(bands)
        assert features["s2_feature_status"] == "ALL_PIXELS_MASKED"
        assert features["s2_spectral_valid_pixels"] == 0
        assert features["s2_spectral_valid_pct"] == 0.0
        assert np.isnan(features["s2_ndvi_mean"])

    def test_all_feature_names_prefixed_with_s2(self, extractor):
        """Verify that every key in the feature dictionary begins with 's2_'."""
        shape = (2, 2)
        bands = {
            "SCL": np.full(shape, 4, dtype=int),
            "B04": np.full(shape, 1000.0),
            "B08": np.full(shape, 3000.0),
            "B11": np.full(shape, 1500.0),
            "B12": np.full(shape, 1200.0),
        }

        features = extractor.extract_features(bands)
        non_prefixed = [k for k in features.keys() if not k.startswith("s2_")]
        assert len(non_prefixed) == 0, f"Found non-prefixed feature keys: {non_prefixed}"
