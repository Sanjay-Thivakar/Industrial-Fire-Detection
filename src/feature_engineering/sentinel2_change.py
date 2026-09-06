"""Sentinel-2 pre/post temporal surface-change feature calculator (Phase 3 — Step 3B).

Takes two independently extracted Step 3A feature dictionaries (pre-event and post-event)
and computes temporal difference features representing optical surface change.

IMPORTANT SCIENTIFIC AND DOMAIN CONSTRAINTS:
1. Change features represent optical surface-change evidence ONLY.
   They do NOT directly prove fire occurrence, industrial fire, or thermal activity.
   Final fire classification combines these features with FIRMS thermal behavior,
   OSM industrial context, WorldCover land context, and independent human validation.
2. Sentinel-2 is an optical multispectral sensor (VNIR/SWIR), NOT a thermal sensor.
   dNBR, dNDVI, and dNDWI reflect changes in surface optical properties between two dates.
3. All output features are strictly prefixed with `s2_`.
4. No live CDSE network access or authentication is performed in this module.
"""

import logging
from typing import Any, Dict, Optional, Set

import numpy as np

logger = logging.getLogger(__name__)

# Step 3A statuses that mean the patch produced usable statistics
_VALID_STATUSES: Set[str] = {"SUCCESS"}

# Indices for which we compute pre/post change statistics
_CHANGE_INDICES = ("ndvi", "nbr", "ndwi", "swir_ratio")

# Statistics used for change computation (matching Step 3A output keys)
_CHANGE_STATS = ("mean", "median")

# Step 3B change feature status values
STATUS_SUCCESS = "SUCCESS"
STATUS_MISSING_PRE = "MISSING_PRE"
STATUS_MISSING_POST = "MISSING_POST"
STATUS_MISSING_BOTH = "MISSING_BOTH"
STATUS_INVALID_INPUT = "INVALID_INPUT"
STATUS_INSUFFICIENT_VALID_DATA = "INSUFFICIENT_VALID_DATA"


class Sentinel2ChangeFeatureCalculator:
    """Calculates temporal pre/post surface-change features from two Step 3A feature dictionaries.

    Consumes the output of Sentinel2SpectralExtractor for a pre-event observation and
    a post-event observation, then computes difference features (dNDVI, dNBR, dNDWI,
    dSWIR_ratio) and absolute differences.

    All produced feature keys are prefixed with `s2_`.
    """

    def __init__(self, min_valid_pct: float = 0.0):
        """Initialize the change feature calculator.

        Args:
            min_valid_pct: Minimum required `s2_spectral_valid_pct` in both pre and post
                           feature dicts to produce change features. Values below this
                           threshold will result in INSUFFICIENT_VALID_DATA status.
                           Default 0.0 allows any non-zero pixel count to proceed.
        """
        self.min_valid_pct = min_valid_pct

    @staticmethod
    def _is_valid_step3a(features: Optional[Dict[str, Any]]) -> bool:
        """Return True only if a Step 3A feature dict has a usable SUCCESS status."""
        if features is None or not isinstance(features, dict):
            return False
        return features.get("s2_feature_status") in _VALID_STATUSES

    @staticmethod
    def _safe_diff(post_val: Any, pre_val: Any) -> float:
        """Compute post - pre safely, returning NaN if either operand is non-finite."""
        try:
            post_f = float(post_val)
            pre_f = float(pre_val)
        except (TypeError, ValueError):
            return np.nan
        if not (np.isfinite(post_f) and np.isfinite(pre_f)):
            return np.nan
        return post_f - pre_f

    def _build_empty_change_dict(
        self,
        status: str,
        reason: str,
        pre_features: Optional[Dict[str, Any]] = None,
        post_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a change feature dict with NaN change values and forwarded quality metadata."""
        result: Dict[str, Any] = {
            "s2_change_status": status,
            "s2_change_failure_reason": reason,
        }

        # Forward pre quality metadata if available
        for key in ("s2_spectral_valid_pixels", "s2_spectral_valid_pct", "s2_feature_status"):
            pre_val = (pre_features or {}).get(key, np.nan if "pct" in key or "pixels" in key else "")
            post_val = (post_features or {}).get(key, np.nan if "pct" in key or "pixels" in key else "")
            result[f"s2_pre_{key[3:]}"] = pre_val   # strip leading "s2_"
            result[f"s2_post_{key[3:]}"] = post_val

        # NaN for all change features
        for idx in _CHANGE_INDICES:
            for stat in _CHANGE_STATS:
                result[f"s2_d{idx}_{stat}"] = np.nan
                result[f"s2_abs_d{idx}_{stat}"] = np.nan

        return result

    def compute_change_features(
        self,
        pre_features: Optional[Dict[str, Any]],
        post_features: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute temporal surface-change features from pre and post Step 3A feature dicts.

        Args:
            pre_features: Feature dictionary from Sentinel2SpectralExtractor for the
                          pre-event Sentinel-2 observation.
            post_features: Feature dictionary from Sentinel2SpectralExtractor for the
                           post-event Sentinel-2 observation.

        Returns:
            Dictionary of change features, all prefixed with `s2_`.
        """
        pre_valid = self._is_valid_step3a(pre_features)
        post_valid = self._is_valid_step3a(post_features)

        # --- Input validation ---
        if pre_features is None and post_features is None:
            return self._build_empty_change_dict(
                STATUS_INVALID_INPUT,
                "Both pre_features and post_features are None.",
            )

        if not pre_valid and not post_valid:
            # Both exist but are both failed/missing
            if pre_features is not None and post_features is not None:
                pre_status = pre_features.get("s2_feature_status", "UNKNOWN")
                post_status = post_features.get("s2_feature_status", "UNKNOWN")
                return self._build_empty_change_dict(
                    STATUS_MISSING_BOTH,
                    f"Both pre ({pre_status}) and post ({post_status}) Step 3A features are unusable.",
                    pre_features,
                    post_features,
                )
            # One is None, other is invalid
            if pre_features is None:
                return self._build_empty_change_dict(
                    STATUS_MISSING_BOTH,
                    "Pre features are None and post features are unusable.",
                    None,
                    post_features,
                )
            return self._build_empty_change_dict(
                STATUS_MISSING_BOTH,
                "Pre features are unusable and post features are None.",
                pre_features,
                None,
            )

        if not pre_valid:
            pre_status = (pre_features or {}).get("s2_feature_status", "NONE")
            return self._build_empty_change_dict(
                STATUS_MISSING_PRE,
                f"Pre Step 3A features are unusable (status: {pre_status}).",
                pre_features,
                post_features,
            )

        if not post_valid:
            post_status = (post_features or {}).get("s2_feature_status", "NONE")
            return self._build_empty_change_dict(
                STATUS_MISSING_POST,
                f"Post Step 3A features are unusable (status: {post_status}).",
                pre_features,
                post_features,
            )

        # --- Minimum valid pixel threshold check ---
        pre_pct = float(pre_features.get("s2_spectral_valid_pct", 0.0))
        post_pct = float(post_features.get("s2_spectral_valid_pct", 0.0))

        if pre_pct < self.min_valid_pct or post_pct < self.min_valid_pct:
            return self._build_empty_change_dict(
                STATUS_INSUFFICIENT_VALID_DATA,
                (
                    f"Valid pixel coverage too low: pre={pre_pct:.1f}%, "
                    f"post={post_pct:.1f}% (threshold={self.min_valid_pct:.1f}%)."
                ),
                pre_features,
                post_features,
            )

        # --- Compute change features ---
        result: Dict[str, Any] = {
            "s2_change_status": STATUS_SUCCESS,
            "s2_change_failure_reason": "",
        }

        # Forward pre/post quality metadata
        for key in ("s2_spectral_valid_pixels", "s2_spectral_valid_pct", "s2_feature_status"):
            result[f"s2_pre_{key[3:]}"] = pre_features.get(key)
            result[f"s2_post_{key[3:]}"] = post_features.get(key)

        # Compute dIndex_stat and abs_dIndex_stat for each index and stat
        for idx in _CHANGE_INDICES:
            for stat in _CHANGE_STATS:
                pre_key = f"s2_{idx}_{stat}"
                post_key = f"s2_{idx}_{stat}"
                diff = self._safe_diff(post_features.get(post_key), pre_features.get(pre_key))
                result[f"s2_d{idx}_{stat}"] = diff
                result[f"s2_abs_d{idx}_{stat}"] = abs(diff) if np.isfinite(diff) else np.nan

        return result
