"""Deterministic unit tests for Sentinel-2 pre/post change feature calculator (Step 3B).

All tests use synthetic Step 3A feature dictionaries with ZERO external dependencies.
"""

import numpy as np
import pytest

from src.feature_engineering.sentinel2_change import (
    Sentinel2ChangeFeatureCalculator,
    STATUS_SUCCESS,
    STATUS_MISSING_PRE,
    STATUS_MISSING_POST,
    STATUS_MISSING_BOTH,
    STATUS_INVALID_INPUT,
    STATUS_INSUFFICIENT_VALID_DATA,
)


def _make_step3a_features(
    ndvi_mean: float = 0.5,
    ndvi_median: float = 0.5,
    nbr_mean: float = 0.4,
    nbr_median: float = 0.4,
    ndwi_mean: float = 0.2,
    ndwi_median: float = 0.2,
    swir_ratio_mean: float = 0.8,
    swir_ratio_median: float = 0.8,
    valid_pct: float = 80.0,
    valid_pixels: int = 2000,
    status: str = "SUCCESS",
) -> dict:
    """Build a minimal synthetic Step 3A feature dictionary."""
    return {
        "s2_feature_status": status,
        "s2_feature_failure_reason": "" if status == "SUCCESS" else "test failure",
        "s2_spectral_valid_pixels": valid_pixels,
        "s2_spectral_valid_pct": valid_pct,
        "s2_ndvi_mean": ndvi_mean,
        "s2_ndvi_median": ndvi_median,
        "s2_nbr_mean": nbr_mean,
        "s2_nbr_median": nbr_median,
        "s2_ndwi_mean": ndwi_mean,
        "s2_ndwi_median": ndwi_median,
        "s2_swir_ratio_mean": swir_ratio_mean,
        "s2_swir_ratio_median": swir_ratio_median,
    }


class TestSentinel2ChangeFeatureCalculator:

    @pytest.fixture
    def calc(self):
        return Sentinel2ChangeFeatureCalculator()

    # ------------------------------------------------------------------
    # 1. Exact difference calculation
    # ------------------------------------------------------------------
    def test_exact_dndvi_mean(self, calc):
        pre = _make_step3a_features(ndvi_mean=0.60)
        post = _make_step3a_features(ndvi_mean=0.35)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS
        assert pytest.approx(result["s2_dndvi_mean"], rel=1e-6) == 0.35 - 0.60   # −0.25

    def test_exact_dnbr_mean(self, calc):
        pre = _make_step3a_features(nbr_mean=0.50)
        post = _make_step3a_features(nbr_mean=0.10)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS
        assert pytest.approx(result["s2_dnbr_mean"], rel=1e-6) == 0.10 - 0.50   # −0.40

    def test_exact_dndwi_mean(self, calc):
        pre = _make_step3a_features(ndwi_mean=0.30)
        post = _make_step3a_features(ndwi_mean=0.20)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS
        assert pytest.approx(result["s2_dndwi_mean"], rel=1e-6) == 0.20 - 0.30  # −0.10

    def test_exact_swir_ratio_change(self, calc):
        pre = _make_step3a_features(swir_ratio_mean=0.60)
        post = _make_step3a_features(swir_ratio_mean=0.90)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS
        assert pytest.approx(result["s2_dswir_ratio_mean"], rel=1e-6) == 0.30

    def test_median_change_computed_independently(self, calc):
        """Median difference must use median stats, not mean stats."""
        pre = _make_step3a_features(ndvi_mean=0.50, ndvi_median=0.48)
        post = _make_step3a_features(ndvi_mean=0.30, ndvi_median=0.33)
        result = calc.compute_change_features(pre, post)

        assert pytest.approx(result["s2_dndvi_mean"], rel=1e-6) == 0.30 - 0.50   # −0.20
        assert pytest.approx(result["s2_dndvi_median"], rel=1e-6) == 0.33 - 0.48  # −0.15

    # ------------------------------------------------------------------
    # 2. Absolute differences
    # ------------------------------------------------------------------
    def test_absolute_dndvi(self, calc):
        pre = _make_step3a_features(ndvi_mean=0.60)
        post = _make_step3a_features(ndvi_mean=0.35)
        result = calc.compute_change_features(pre, post)

        assert pytest.approx(result["s2_abs_dndvi_mean"], rel=1e-6) == 0.25

    def test_absolute_dnbr_positive_case(self, calc):
        """abs_dNBR is always non-negative."""
        pre = _make_step3a_features(nbr_mean=0.10)
        post = _make_step3a_features(nbr_mean=0.50)
        result = calc.compute_change_features(pre, post)

        assert result["s2_dnbr_mean"] > 0
        assert pytest.approx(result["s2_abs_dnbr_mean"], rel=1e-6) == abs(result["s2_dnbr_mean"])

    # ------------------------------------------------------------------
    # 3. Missing pre / post
    # ------------------------------------------------------------------
    def test_missing_pre_none(self, calc):
        post = _make_step3a_features()
        result = calc.compute_change_features(None, post)

        assert result["s2_change_status"] == STATUS_MISSING_PRE  # None pre with valid post
        assert np.isnan(result["s2_dndvi_mean"])

    def test_missing_pre_invalid_status(self, calc):
        pre = _make_step3a_features(status="ALL_PIXELS_MASKED")
        post = _make_step3a_features()
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_MISSING_PRE
        assert np.isnan(result["s2_dndvi_mean"])
        assert np.isnan(result["s2_dnbr_mean"])

    def test_missing_post_invalid_status(self, calc):
        pre = _make_step3a_features()
        post = _make_step3a_features(status="MISSING_BAND")
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_MISSING_POST
        assert np.isnan(result["s2_dnbr_mean"])

    def test_missing_both_none(self, calc):
        result = calc.compute_change_features(None, None)
        assert result["s2_change_status"] == STATUS_INVALID_INPUT

    def test_missing_both_invalid_statuses(self, calc):
        pre = _make_step3a_features(status="ALL_PIXELS_MASKED")
        post = _make_step3a_features(status="DIMENSION_MISMATCH")
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_MISSING_BOTH
        assert np.isnan(result["s2_dndvi_mean"])

    # ------------------------------------------------------------------
    # 4. NaN inputs from Step 3A
    # ------------------------------------------------------------------
    def test_nan_pre_ndvi_produces_nan_diff(self, calc):
        pre = _make_step3a_features(ndvi_mean=np.nan)
        post = _make_step3a_features(ndvi_mean=0.40)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS
        assert np.isnan(result["s2_dndvi_mean"])
        assert np.isnan(result["s2_abs_dndvi_mean"])

    def test_nan_post_nbr_produces_nan_diff(self, calc):
        pre = _make_step3a_features(nbr_mean=0.50)
        post = _make_step3a_features(nbr_mean=np.nan)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS
        assert np.isnan(result["s2_dnbr_mean"])

    # ------------------------------------------------------------------
    # 5. Insufficient valid data threshold
    # ------------------------------------------------------------------
    def test_insufficient_valid_pct_pre(self):
        calc = Sentinel2ChangeFeatureCalculator(min_valid_pct=50.0)
        pre = _make_step3a_features(valid_pct=30.0)  # too low
        post = _make_step3a_features(valid_pct=85.0)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_INSUFFICIENT_VALID_DATA
        assert np.isnan(result["s2_dndvi_mean"])

    def test_sufficient_valid_pct(self):
        calc = Sentinel2ChangeFeatureCalculator(min_valid_pct=50.0)
        pre = _make_step3a_features(valid_pct=80.0)
        post = _make_step3a_features(valid_pct=90.0)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS

    # ------------------------------------------------------------------
    # 6. Quality metadata forwarding
    # ------------------------------------------------------------------
    def test_pre_post_quality_forwarded(self, calc):
        pre = _make_step3a_features(valid_pct=72.0, valid_pixels=1800)
        post = _make_step3a_features(valid_pct=88.0, valid_pixels=2200)
        result = calc.compute_change_features(pre, post)

        assert result["s2_change_status"] == STATUS_SUCCESS
        assert result["s2_pre_spectral_valid_pct"] == 72.0
        assert result["s2_pre_spectral_valid_pixels"] == 1800
        assert result["s2_post_spectral_valid_pct"] == 88.0
        assert result["s2_post_spectral_valid_pixels"] == 2200

    # ------------------------------------------------------------------
    # 7. All output keys prefixed with s2_
    # ------------------------------------------------------------------
    def test_all_change_keys_prefixed_s2(self, calc):
        pre = _make_step3a_features()
        post = _make_step3a_features()
        result = calc.compute_change_features(pre, post)

        bad = [k for k in result if not k.startswith("s2_")]
        assert len(bad) == 0, f"Found non-s2_ prefixed keys: {bad}"
