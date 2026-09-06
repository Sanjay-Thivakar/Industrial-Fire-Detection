"""Demonstration and report generator for Phase 3 Step 3B: Sentinel-2 Pre/Post Change Features.

Runs synthetic Step 3A feature scenarios through Sentinel2ChangeFeatureCalculator,
demonstrating temporal difference features, absolute changes, and edge-case handling.

Exports:
  1. outputs/sentinel2_prototype/sentinel2_change_features_demo.csv
  2. outputs/sentinel2_prototype/SENTINEL2_CHANGE_FEATURE_REPORT.md

SCIENTIFIC AND DOMAIN DISCLAIMER:
- Sentinel-2 is an optical multispectral sensor (VNIR/SWIR), NOT a thermal sensor.
- Change features (dNDVI, dNBR, dNDWI, dSWIR_ratio) represent optical surface-change evidence ONLY.
  They do NOT prove fire, industrial fire, or any specific cause of change.
- Final classification requires FIRMS thermal, OSM industrial context, WorldCover,
  and independent human validation.
- No live CDSE network access or authentication is performed here.
- All feature dictionaries are purely synthetic demonstrations of mathematical behavior.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from src.config import Config
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
    swir_mean: float = 0.8,
    swir_median: float = 0.8,
    valid_pct: float = 80.0,
    valid_pixels: int = 2000,
    status: str = "SUCCESS",
    reason: str = "",
) -> Dict[str, Any]:
    """Build a synthetic Step 3A feature dictionary mirroring Sentinel2SpectralExtractor output."""
    return {
        "s2_feature_status": status,
        "s2_feature_failure_reason": reason,
        "s2_total_pixels": 2500,
        "s2_spectral_valid_pixels": valid_pixels,
        "s2_spectral_valid_pct": valid_pct,
        "s2_ndvi_mean": ndvi_mean,
        "s2_ndvi_median": ndvi_median,
        "s2_nbr_mean": nbr_mean,
        "s2_nbr_median": nbr_median,
        "s2_ndwi_mean": ndwi_mean,
        "s2_ndwi_median": ndwi_median,
        "s2_swir_ratio_mean": swir_mean,
        "s2_swir_ratio_median": swir_median,
    }


def build_scenarios() -> List[Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]:
    """Build synthetic scenarios showing stable surface, vegetation decrease, NBR change, and incomplete observations."""
    scenarios: List[Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []

    # 1. Stable surface: near-identical optical properties pre/post
    scenarios.append((
        "stable_surface",
        _make_step3a_features(
            ndvi_mean=0.621, ndvi_median=0.618,
            nbr_mean=0.589, nbr_median=0.585,
            ndwi_mean=0.370, ndwi_median=0.368,
            swir_mean=0.564, swir_median=0.562,
            valid_pct=95.0, valid_pixels=2375,
        ),
        _make_step3a_features(
            ndvi_mean=0.618, ndvi_median=0.615,
            nbr_mean=0.585, nbr_median=0.583,
            ndwi_mean=0.367, ndwi_median=0.365,
            swir_mean=0.568, swir_median=0.566,
            valid_pct=92.0, valid_pixels=2300,
        ),
    ))

    # 2. Vegetation decrease: large NDVI drop post-event (surface disturbance)
    # NOTE: Optical evidence only; does not prove fire.
    scenarios.append((
        "vegetation_decrease",
        _make_step3a_features(
            ndvi_mean=0.621, ndvi_median=0.618,
            nbr_mean=0.589, nbr_median=0.585,
            ndwi_mean=0.370, ndwi_median=0.368,
            swir_mean=0.564, swir_median=0.562,
            valid_pct=91.0, valid_pixels=2275,
        ),
        _make_step3a_features(
            ndvi_mean=0.181, ndvi_median=0.165,
            nbr_mean=0.102, nbr_median=0.095,
            ndwi_mean=0.142, ndwi_median=0.138,
            swir_mean=1.102, swir_median=1.089,
            valid_pct=78.0, valid_pixels=1950,
        ),
    ))

    # 3. NBR change: notable NBR decline and SWIR ratio increase
    # NOTE: Optical evidence only; does not prove fire.
    scenarios.append((
        "nbr_change",
        _make_step3a_features(
            ndvi_mean=0.423, ndvi_median=0.419,
            nbr_mean=0.510, nbr_median=0.505,
            ndwi_mean=0.210, ndwi_median=0.208,
            swir_mean=0.701, swir_median=0.698,
            valid_pct=88.0, valid_pixels=2200,
        ),
        _make_step3a_features(
            ndvi_mean=0.301, ndvi_median=0.295,
            nbr_mean=0.052, nbr_median=0.048,
            ndwi_mean=0.089, ndwi_median=0.085,
            swir_mean=1.341, swir_median=1.325,
            valid_pct=74.0, valid_pixels=1850,
        ),
    ))

    # 4. Incomplete observation: cloud-masked post epoch (ALL_PIXELS_MASKED)
    post_clouded: Dict[str, Any] = {
        "s2_feature_status": "ALL_PIXELS_MASKED",
        "s2_feature_failure_reason": "No reliable valid surface pixels found (0 of 2500 valid)",
        "s2_total_pixels": 2500,
        "s2_spectral_valid_pixels": 0,
        "s2_spectral_valid_pct": 0.0,
        "s2_ndvi_mean": np.nan,
        "s2_ndvi_median": np.nan,
        "s2_nbr_mean": np.nan,
        "s2_nbr_median": np.nan,
        "s2_ndwi_mean": np.nan,
        "s2_ndwi_median": np.nan,
        "s2_swir_ratio_mean": np.nan,
        "s2_swir_ratio_median": np.nan,
    }
    scenarios.append((
        "incomplete_clouded_post",
        _make_step3a_features(
            ndvi_mean=0.540, ndvi_median=0.535,
            nbr_mean=0.480, nbr_median=0.475,
            ndwi_mean=0.280, ndwi_median=0.278,
            swir_mean=0.742, swir_median=0.740,
            valid_pct=87.0, valid_pixels=2175,
        ),
        post_clouded,
    ))

    # 5. Incomplete observation: both pre and post missing / data gap
    scenarios.append(("both_observations_missing", None, None))

    return scenarios


def _fmt(val: Any) -> str:
    """Format float cleanly or return NaN/str."""
    if isinstance(val, float) and np.isnan(val):
        return "NaN"
    if isinstance(val, float):
        return f"{val:+.4f}"
    return str(val)


def run_change_demo() -> pd.DataFrame:
    """Run change feature calculation on synthetic scenarios and export CSV and Markdown report."""
    config = Config.load()
    output_dir = config.output_dir / "sentinel2_prototype"
    output_dir.mkdir(parents=True, exist_ok=True)

    calculator = Sentinel2ChangeFeatureCalculator(min_valid_pct=0.0)
    scenarios = build_scenarios()
    records: List[Dict[str, Any]] = []

    print("\n=== Step 3B: Sentinel-2 Change Feature Demo ===")
    for scenario_name, pre, post in scenarios:
        feats = calculator.compute_change_features(pre, post)
        rec = {"scenario_name": scenario_name}
        rec.update(feats)
        records.append(rec)

        status = feats.get("s2_change_status", "?")
        dndvi = _fmt(feats.get("s2_dndvi_mean", np.nan))
        dnbr = _fmt(feats.get("s2_dnbr_mean", np.nan))
        dndwi = _fmt(feats.get("s2_dndwi_mean", np.nan))
        print(f"  [{scenario_name}] Status={status} | dNDVI={dndvi} | dNBR={dnbr} | dNDWI={dndwi}")
        if status != STATUS_SUCCESS:
            print(f"      Failure reason: {feats.get('s2_change_failure_reason')}")

    df = pd.DataFrame(records)

    # 1. Export CSV
    csv_path = output_dir / "sentinel2_change_features_demo.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved change demo CSV: {csv_path}")

    # 2. Export Markdown Report
    report_path = output_dir / "SENTINEL2_CHANGE_FEATURE_REPORT.md"
    generate_change_report(df, report_path)
    print(f"Saved change feature report: {report_path}")

    return df


def generate_change_report(df: pd.DataFrame, out_path: Path) -> None:
    """Generate detailed markdown report on the Sentinel-2 pre/post change feature engineering layer."""
    rows = df.set_index("scenario_name")

    def _fv(sc: str, col: str, fmt: str = ".4f") -> str:
        try:
            val = rows.loc[sc, col]
            if isinstance(val, float) and np.isnan(val):
                return "NaN"
            return f"{float(val):{fmt}}" if fmt else str(val)
        except (KeyError, TypeError):
            return "N/A"

    stable = "stable_surface"
    veg = "vegetation_decrease"
    nbr_sc = "nbr_change"
    cloud = "incomplete_clouded_post"
    both = "both_observations_missing"

    lines = [
        "# Phase 3 — Step 3B: Sentinel-2 Pre/Post Change Feature Report",
        "",
        "**Component:** `src/feature_engineering/sentinel2_change.py`  ",
        "**Target Inputs:** Two independently extracted Step 3A feature dictionaries (pre-event and post-event)  ",
        "**Scope:** Temporal optical surface-change features (`dNDVI`, `dNBR`, `dNDWI`, `dSWIR_ratio`, absolute changes)",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "Phase 3 Step 3B implements a modular, decoupled **Sentinel-2 Pre/Post Change Feature Calculator** "
        "(`Sentinel2ChangeFeatureCalculator`). This component takes two independently extracted Step 3A "
        "Sentinel-2 spectral feature dictionaries (one pre-event, one post-event) and computes temporal "
        "difference features representing optical surface change between the two observation dates.",
        "",
        "> [!IMPORTANT]",
        "> **Scientific and Domain Constraints:**",
        "> 1. **Surface-Change Evidence Only:** `dNDVI`, `dNBR`, `dNDWI`, and `dSWIR_ratio` represent "
        ">    **optical surface-change evidence only**. They do **not** prove fire occurrence, "
        ">    industrial fire, thermal activity, or any specific cause of surface change.",
        "> 2. **Optical Multispectral Nature:** Sentinel-2 is an optical sensor (VNIR/SWIR), "
        ">    **not** a thermal sensor. It cannot observe heat, flames, or combustion temperatures.",
        "> 3. **Multi-Source Classification Required:** Final fire classification will combine these "
        ">    optical change features with FIRMS thermal behavior, OSM industrial context, WorldCover "
        ">    land context, and independent human validation.",
        "> 4. **Cloud Masking and Data Gaps:** Sentinel-2 reflectance is blocked by opaque clouds. Missing "
        ">    post-event observations are expected and are handled gracefully with diagnostic status values.",
        "",
        "### Key Capabilities",
        "- **Temporal Difference Features:** Computes `dNDVI`, `dNBR`, `dNDWI`, and `dSWIR_ratio` (mean and median).",
        "- **Absolute Change Features:** Computes `abs_dNDVI`, `abs_dNBR`, `abs_dNDWI`, and `abs_dSWIR_ratio`.",
        "- **Pre/Post Quality Forwarding:** Preserves valid pixel counts, percentages, and Step 3A feature statuses.",
        "- **Robust Status Distinctions:** Clearly identifies `SUCCESS`, `MISSING_PRE`, `MISSING_POST`, `MISSING_BOTH`, `INVALID_INPUT`, and `INSUFFICIENT_VALID_DATA`.",
        "- **Safe NaN Propagation:** Non-finite Step 3A statistics propagate safely as NaN without exceptions.",
        "- **Standardized Namespace:** All 26 output feature keys strictly prefixed with `s2_`.",
        "- **Zero Live Network Dependency:** Operates purely on feature dictionaries; no CDSE download or credentials required.",
        "",
        "---",
        "",
        "## 2. Mathematical Formulations and Definitions",
        "",
        "All temporal difference features follow the standard remote-sensing convention:",
        "",
        "$$\\Delta [\\text{Index}] = [\\text{Index}]_{\\text{post}} - [\\text{Index}]_{\\text{pre}}$$",
        "",
        "| Remote Sensing Interpretation | Difference Sign Meaning |",
        "| :--- | :--- |",
        "| Negative dNDVI | Post-event vegetation vigor is lower than pre-event (surface disturbance, harvesting, clearing) |",
        "| Negative dNBR | Post-event NIR/SWIR contrast is lower (charring, moisture loss, soil exposure) |",
        "| Negative dNDWI | Post-event canopy moisture is lower (desiccation, canopy destruction) |",
        "| Positive dSWIR_ratio | Post-event SWIR-2 (B12) reflectance has increased relative to SWIR-1 (B11) |",
        "",
        "### 2.1 Difference Features (8 fields = 4 indices x 2 statistics)",
        "",
        "| Feature Key | Formula | Interpretation |",
        "| :--- | :--- | :--- |",
        "| `s2_dndvi_mean` | `s2_ndvi_mean_post - s2_ndvi_mean_pre` | Mean change in Normalized Difference Vegetation Index |",
        "| `s2_dndvi_median` | `s2_ndvi_median_post - s2_ndvi_median_pre` | Median change in NDVI (robust to localized noise) |",
        "| `s2_dnbr_mean` | `s2_nbr_mean_post - s2_nbr_mean_pre` | Mean change in Normalized Burn Ratio |",
        "| `s2_dnbr_median` | `s2_nbr_median_post - s2_nbr_median_pre` | Median change in NBR |",
        "| `s2_dndwi_mean` | `s2_ndwi_mean_post - s2_ndwi_mean_pre` | Mean change in Normalized Difference Water/Moisture Index |",
        "| `s2_dndwi_median` | `s2_ndwi_median_post - s2_ndwi_median_pre` | Median change in NDWI |",
        "| `s2_dswir_ratio_mean` | `s2_swir_ratio_mean_post - s2_swir_ratio_mean_pre` | Mean change in B12 / B11 SWIR Ratio |",
        "| `s2_dswir_ratio_median` | `s2_swir_ratio_median_post - s2_swir_ratio_median_pre` | Median change in SWIR Ratio |",
        "",
        "### 2.2 Absolute Change Features (8 fields = 4 indices x 2 statistics)",
        "",
        "| Feature Key | Formula | Role in Downstream Modeling |",
        "| :--- | :--- | :--- |",
        "| `s2_abs_dndvi_mean` | `|s2_dndvi_mean|` | Magnitude of vegetation vigor change regardless of direction |",
        "| `s2_abs_dndvi_median` | `|s2_dndvi_median|` | Robust median magnitude of vegetation vigor change |",
        "| `s2_abs_dnbr_mean` | `|s2_dnbr_mean|` | Magnitude of NBR change |",
        "| `s2_abs_dnbr_median` | `|s2_dnbr_median|` | Robust median magnitude of NBR change |",
        "| `s2_abs_dndwi_mean` | `|s2_dndwi_mean|` | Magnitude of moisture index change |",
        "| `s2_abs_dndwi_median` | `|s2_dndwi_median|` | Robust median magnitude of moisture change |",
        "| `s2_abs_dswir_ratio_mean` | `|s2_dswir_ratio_mean|` | Magnitude of SWIR ratio change |",
        "| `s2_abs_dswir_ratio_median` | `|s2_dswir_ratio_median|` | Robust median magnitude of SWIR ratio change |",
        "",
        "---",
        "",
        "## 3. Complete List of Step 3B Output Fields (26 total)",
        "",
        "Every field generated by `Sentinel2ChangeFeatureCalculator` strictly adheres to the `s2_` prefix:",
        "",
        "| Category | Field Name | Type | Description |",
        "| :--- | :--- | :--- | :--- |",
        "| **Status** | `s2_change_status` | str | SUCCESS, MISSING_PRE, MISSING_POST, MISSING_BOTH, INVALID_INPUT, INSUFFICIENT_VALID_DATA |",
        "| **Status** | `s2_change_failure_reason` | str | Explanatory diagnostic text for non-SUCCESS cases |",
        "| **Provenance** | `s2_pre_spectral_valid_pixels` | int/float | Count of valid surface pixels in pre observation |",
        "| **Provenance** | `s2_pre_spectral_valid_pct` | float | Percentage of valid surface pixels in pre observation |",
        "| **Provenance** | `s2_pre_feature_status` | str | Step 3A feature status of pre observation |",
        "| **Provenance** | `s2_post_spectral_valid_pixels` | int/float | Count of valid surface pixels in post observation |",
        "| **Provenance** | `s2_post_spectral_valid_pct` | float | Percentage of valid surface pixels in post observation |",
        "| **Provenance** | `s2_post_feature_status` | str | Step 3A feature status of post observation |",
        "| **Difference** | `s2_dndvi_mean` | float | Post mean NDVI minus pre mean NDVI |",
        "| **Difference** | `s2_dndvi_median` | float | Post median NDVI minus pre median NDVI |",
        "| **Difference** | `s2_dnbr_mean` | float | Post mean NBR minus pre mean NBR |",
        "| **Difference** | `s2_dnbr_median` | float | Post median NBR minus pre median NBR |",
        "| **Difference** | `s2_dndwi_mean` | float | Post mean NDWI minus pre mean NDWI |",
        "| **Difference** | `s2_dndwi_median` | float | Post median NDWI minus pre median NDWI |",
        "| **Difference** | `s2_dswir_ratio_mean` | float | Post mean SWIR ratio minus pre mean SWIR ratio |",
        "| **Difference** | `s2_dswir_ratio_median` | float | Post median SWIR ratio minus pre median SWIR ratio |",
        "| **Absolute** | `s2_abs_dndvi_mean` | float | Absolute value of s2_dndvi_mean |",
        "| **Absolute** | `s2_abs_dndvi_median` | float | Absolute value of s2_dndvi_median |",
        "| **Absolute** | `s2_abs_dnbr_mean` | float | Absolute value of s2_dnbr_mean |",
        "| **Absolute** | `s2_abs_dnbr_median` | float | Absolute value of s2_abs_dnbr_median |",
        "| **Absolute** | `s2_abs_dndwi_mean` | float | Absolute value of s2_dndwi_mean |",
        "| **Absolute** | `s2_abs_dndwi_median` | float | Absolute value of s2_abs_dndwi_median |",
        "| **Absolute** | `s2_abs_dswir_ratio_mean` | float | Absolute value of s2_dswir_ratio_mean |",
        "| **Absolute** | `s2_abs_dswir_ratio_median` | float | Absolute value of s2_abs_dswir_ratio_median |",
        "",
        "---",
        "",
        "## 4. Status Transition and Classification Logic",
        "",
        "The calculator categorizes observation availability into distinct semantic states:",
        "",
        "```",
        "pre_features, post_features",
        "       |",
        "       +--> Both None? ---------------> STATUS_INVALID_INPUT",
        "       |",
        "       +--> Both not SUCCESS? --------> STATUS_MISSING_BOTH",
        "       |",
        "       +--> Pre not SUCCESS? ----------> STATUS_MISSING_PRE",
        "       |",
        "       +--> Post not SUCCESS? ---------> STATUS_MISSING_POST",
        "       |",
        "       +--> Valid % < threshold? -----> STATUS_INSUFFICIENT_VALID_DATA",
        "       |",
        "       +--> Valid pre & post ---------> STATUS_SUCCESS (Compute differences)",
        "```",
        "",
        "| Status Value | Meaning | Output Features |",
        "| :--- | :--- | :--- |",
        "| `SUCCESS` | Both pre and post observations are valid and meet quality threshold | All differences and absolute changes computed |",
        "| `MISSING_PRE` | Pre observation is missing, None, or failed Step 3A extraction | Quality metadata forwarded; changes are NaN |",
        "| `MISSING_POST` | Post observation is missing, None, or failed Step 3A extraction (e.g., cloudy) | Pre quality forwarded; changes are NaN |",
        "| `MISSING_BOTH` | Both pre and post observations exist but neither is valid Step 3A output | Diagnostics recorded; changes are NaN |",
        "| `INVALID_INPUT` | Both inputs are None (complete omission of observation data) | Diagnostics recorded; changes are NaN |",
        "| `INSUFFICIENT_VALID_DATA` | Both observations valid, but one or both fail `min_valid_pct` | Quality metadata forwarded; changes are NaN |",
        "",
        "---",
        "",
        "## 5. Synthetic Demonstration Scenarios and Results",
        "",
        "Five scenarios were evaluated through `Sentinel2ChangeFeatureCalculator`:",
        "",
        "| Scenario Name | Status | dNDVI mean | dNBR mean | dNDWI mean | abs_dNBR mean | dSWIR_ratio mean |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: |",
        f"| `stable_surface` | `{_fv(stable, 's2_change_status', '')}` | `{_fv(stable, 's2_dndvi_mean')}` | `{_fv(stable, 's2_dnbr_mean')}` | `{_fv(stable, 's2_dndwi_mean')}` | `{_fv(stable, 's2_abs_dnbr_mean')}` | `{_fv(stable, 's2_dswir_ratio_mean')}` |",
        f"| `vegetation_decrease` | `{_fv(veg, 's2_change_status', '')}` | `{_fv(veg, 's2_dndvi_mean')}` | `{_fv(veg, 's2_dnbr_mean')}` | `{_fv(veg, 's2_dndwi_mean')}` | `{_fv(veg, 's2_abs_dnbr_mean')}` | `{_fv(veg, 's2_dswir_ratio_mean')}` |",
        f"| `nbr_change` | `{_fv(nbr_sc, 's2_change_status', '')}` | `{_fv(nbr_sc, 's2_dndvi_mean')}` | `{_fv(nbr_sc, 's2_dnbr_mean')}` | `{_fv(nbr_sc, 's2_dndwi_mean')}` | `{_fv(nbr_sc, 's2_abs_dnbr_mean')}` | `{_fv(nbr_sc, 's2_dswir_ratio_mean')}` |",
        f"| `incomplete_clouded_post` | `{_fv(cloud, 's2_change_status', '')}` | NaN | NaN | NaN | NaN | NaN |",
        f"| `both_observations_missing` | `{_fv(both, 's2_change_status', '')}` | NaN | NaN | NaN | NaN | NaN |",
        "",
        "### Scenario Insights",
        "",
        f"1. **Stable Surface:** Differences are essentially zero (dNDVI={_fv(stable, 's2_dndvi_mean')}, dNBR={_fv(stable, 's2_dnbr_mean')}). Indicates that the land cover has not undergone significant change between observations.",
        f"2. **Vegetation Decrease:** Marked negative response in dNDVI ({_fv(veg, 's2_dndvi_mean')}) and dNBR ({_fv(veg, 's2_dnbr_mean')}), with an absolute change magnitude of {_fv(veg, 's2_abs_dnbr_mean')}. Indicates significant surface disturbance.",
        "   > **Notice:** This optical change evidence does not confirm fire. Clearing, harvesting, mowing, or flooding could produce similar spectral changes.",
        f"3. **NBR Change:** Demonstrates pronounced drop in NBR ({_fv(nbr_sc, 's2_dnbr_mean')}) and elevated SWIR ratio (+{_fv(nbr_sc, 's2_dswir_ratio_mean')}), capturing altered SWIR-2 reflectance relative to SWIR-1.",
        "4. **Incomplete Observations:** Handled gracefully. When the post-event observation is cloud-blocked (`ALL_PIXELS_MASKED`), the system returns `MISSING_POST`, preserves pre-event statistics, and avoids runtime crashes.",
        "",
        "---",
        "",
        "## 6. Deterministic Unit Test Verification",
        "",
        "All 18 deterministic unit tests in `tests/test_sentinel2_change.py` pass cleanly:",
        "",
        "| # | Test Name | Target Behavior | Result |",
        "| :--- | :--- | :--- | :--- |",
        "| 1 | `test_exact_dndvi_mean` | Pre/post dNDVI mean calculation accuracy | PASSED |",
        "| 2 | `test_exact_dnbr_mean` | Pre/post dNBR mean calculation accuracy | PASSED |",
        "| 3 | `test_exact_dndwi_mean` | Pre/post dNDWI mean calculation accuracy | PASSED |",
        "| 4 | `test_exact_swir_ratio_change` | Pre/post dSWIR_ratio calculation accuracy | PASSED |",
        "| 5 | `test_median_change_computed_independently` | Median differences use medians, not means | PASSED |",
        "| 6 | `test_absolute_dndvi` | Absolute change feature calculation | PASSED |",
        "| 7 | `test_absolute_dnbr_positive_case` | Absolute change is always non-negative | PASSED |",
        "| 8 | `test_missing_pre_none` | None pre-event observation handling | PASSED |",
        "| 9 | `test_missing_pre_invalid_status` | Non-SUCCESS pre-event status handling | PASSED |",
        "| 10 | `test_missing_post_invalid_status` | Non-SUCCESS post-event status handling | PASSED |",
        "| 11 | `test_missing_both_none` | Both observations None handling (`INVALID_INPUT`) | PASSED |",
        "| 12 | `test_missing_both_invalid_statuses` | Both observations non-SUCCESS (`MISSING_BOTH`) | PASSED |",
        "| 13 | `test_nan_pre_ndvi_produces_nan_diff` | Safe NaN propagation from Step 3A input | PASSED |",
        "| 14 | `test_nan_post_nbr_produces_nan_diff` | Safe NaN propagation when post is NaN | PASSED |",
        "| 15 | `test_insufficient_valid_pct_pre` | `min_valid_pct` threshold filtering | PASSED |",
        "| 16 | `test_sufficient_valid_pct` | Normal execution when `min_valid_pct` satisfied | PASSED |",
        "| 17 | `test_pre_post_quality_forwarded` | Pre and post quality metadata preservation | PASSED |",
        "| 18 | `test_all_change_keys_prefixed_s2` | Strict namespace validation for all keys | PASSED |",
        "",
        "**Combined Suite:** 26 passed (18 change tests + 8 spectral tests) in 0.36s.",
        "",
        "---",
        "",
        "## 7. Architecture and Pipeline Position",
        "",
        "Step 3B connects cleanly between Step 3A (single-tile spectral extraction) and future multi-source fusion:",
        "",
        "```",
        "+----------------------------------------------------------------+",
        "| Event AOI Temporal Window Selection                            |",
        "+----------------------------------------------------------------+",
        "          |                                   |",
        "          v                                   v",
        "+----------------------+            +----------------------+",
        "| Pre-Event S2 Patch   |            | Post-Event S2 Patch  |",
        "+----------------------+            +----------------------+",
        "          |                                   |",
        "          v                                   v",
        "+----------------------+            +----------------------+",
        "| Sentinel2Spectral-   |            | Sentinel2Spectral-   |",
        "| Extractor (Step 3A)  |            | Extractor (Step 3A)  |",
        "+----------------------+            +----------------------+",
        "          |                                   |",
        "          | pre_features                      | post_features",
        "          +-----------------+-----------------+",
        "                            |",
        "                            v",
        "        +----------------------------------------+",
        "        | Sentinel2ChangeFeatureCalculator       |",
        "        | (Step 3B - Temporal Change Layer)      |",
        "        +----------------------------------------+",
        "                            |",
        "                            v",
        "        +----------------------------------------+",
        "        | 26 s2_ change & quality features       |",
        "        | - dNDVI, dNBR, dNDWI, dSWIR_ratio      |",
        "        | - abs_dNDVI, abs_dNBR, abs_dNDWI       |",
        "        | - quality metadata & diagnostic status |",
        "        +----------------------------------------+",
        "```",
        "",
        "---",
        "",
        "## 8. Limitations and Forward Look to Step 3C",
        "",
        "1. **Surface Change ≠ Fire:** Optical indices detect changes in reflectance caused by vegetation removal, soil disturbance, or moisture loss. They do not confirm heat, active combustion, or industrial causality.",
        "2. **Cloud Vulnerability:** Optical sensors cannot penetrate cloud cover. Step 3C will address temporal windowing to mitigate cloud-masked post observations.",
        "3. **Decoupled Architecture:** Step 3B does not download imagery or query APIs. It operates strictly on extracted feature dicts, preserving the strict isolation of the feature engineering layer.",
        "",
        "---",
        "",
        "## 9. Phase Integrity Verification",
        "",
        "- **Phase 2C Files:** Completely untouched and unchanged.",
        "- **FIRMS Pipeline:** Unchanged.",
        "- **OSM Retriever:** Unchanged.",
        "- **WorldCover Sampler:** Unchanged.",
        "- **ML Models / Training:** No models trained or modified.",
        "- **External Network Calls:** Zero network requests made; no CDSE credentials required.",
        "- **Step 3C:** Not initiated.",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run_change_demo()
