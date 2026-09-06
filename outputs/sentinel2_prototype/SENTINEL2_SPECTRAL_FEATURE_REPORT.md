# Phase 3 — Step 3A: Sentinel-2 Spectral Feature Extraction Report

**Component:** `src/feature_engineering/sentinel2_spectral.py`  
**Target Inputs:** Localized Sentinel-2 Level-2A 5-band AOI (`SCL`, `B04`, `B08`, `B11`, `B12`)  
**Scope:** Single-patch optical spectral feature extraction (pre/post change deferred to Step 3B)  

---

## 1. Executive Summary

We have designed and implemented a modular, decoupled **Sentinel-2 Spectral Feature Extraction Engine** (`Sentinel2SpectralExtractor`).

### Key Capabilities
- **Strict SCL Surface Screening:** Accepts only reliable valid surface pixels (classes `4`, `5`, `6`). Excludes `0, 1, 2, 3, 7, 8, 9, 10, 11`.
- **Pixel-Level Spectral Indices:** Evaluates NDVI, NBR, NDWI, and experimental SWIR Ratio (B12 / B11) on valid surface pixels with safe zero-division handling.
- **Summary Statistics:** Computes `mean`, `median`, `std`, `min`, `max`, and `valid_count` for indices, and `mean`, `median`, `std` for raw bands.
- **Standardized Namespace:** Every extracted feature and quality field is strictly prefixed with `s2_`.
- **Zero Live Network Dependency:** Fully testable and operable with synthetic arrays; no live CDSE download or credentials required for Step 3A.

> [!IMPORTANT]
> **Scientific & Domain Constraints**:
> 1. **Optical Multispectral Nature**: Sentinel-2 is an optical sensor (VNIR/SWIR), **not** a thermal sensor. These spectral features represent optical surface condition, moisture, and ground vegetation vigor. They do **not** directly measure thermal plumes or flame temperatures.
> 2. **Synthetic Demonstration Disclaimer**:
>    The synthetic disturbed/burned scenario demonstrates mathematical feature behavior only. It is **not** validation of fire detection, burn detection, or industrial-fire classification.
> 3. **SWIR Ratio Framing**:
>    SWIR Ratio = B12 / B11 is retained strictly as an additional SWIR spectral feature for later empirical evaluation on validated ground truth.

---

## 2. Bands and SCL Classification Rules

### 2.1 Required Input Bands
| Band | Spectral Domain | Central Wavelength | Native Resolution | Primary Role |
| :--- | :--- | :--- | :--- | :--- |
| **SCL** | Scene Classification | Categorical (0–11) | 20 m | Pixel quality & surface screening |
| **B04** | Red | ~665 nm | 10 m | Chlorophyll absorption, NDVI denominator |
| **B08** | Near Infrared (NIR) | ~842 nm | 10 m | Vegetation structure, moisture, NBR/NDVI |
| **B11** | Shortwave Infrared 1 (SWIR-1) | ~1610 nm | 20 m | Moisture content, NDWI, SWIR ratio denominator |
| **B12** | Shortwave Infrared 2 (SWIR-2) | ~2190 nm | 20 m | Soil/rock/charred surface response, NBR denominator |

### 2.2 SCL Pixel Screening Rules
Only pixels matching reliable surface classes are admitted into feature calculation:
- **Accepted as Valid Surface:**
  - Class `4`: Vegetation
  - Class `5`: Not Vegetated / Bare Surface
  - Class `6`: Water
- **Strictly Excluded:**
  - Class `0`: No Data
  - Class `1`: Saturated / Defective Pixels
  - Class `2`: Dark Area Pixels *(preserved separately; not assumed valid)*
  - Class `3`: Cloud Shadows
  - Class `7`: Unclassified *(quarantined; not treated as valid)*
  - Class `8`: Cloud Medium Probability
  - Class `9`: Cloud High Probability
  - Class `10`: Thin Cirrus
  - Class `11`: Snow / Ice

---

## 3. Mathematical Formulas and Indices

All indices are computed element-wise on valid pixels with safe division:

1. **Normalized Difference Vegetation Index (NDVI)**:
   $$\text{NDVI} = \frac{B08 - B04}{B08 + B04}$$
   *Measures chlorophyll vigor and green vegetation density.*

2. **Normalized Burn Ratio (NBR)**:
   $$\text{NBR} = \frac{B08 - B12}{B08 + B12}$$
   *Contrasts NIR vegetation reflectance with SWIR ground reflectance.*

3. **Normalized Difference Water Index (NDWI)**:
   $$\text{NDWI} = \frac{B08 - B11}{B08 + B11}$$
   *Sensitive to vegetation liquid water and canopy moisture.*

4. **SWIR Ratio**:
   $$\text{SWIR Ratio} = \frac{B12}{B11}$$
   *An additional SWIR spectral feature retained for later empirical evaluation.*

---

## 4. Complete List of Generated Sentinel-2 Features

The engine outputs 41 standardized `s2_` fields:

### Quality & Operational Metadata (5 fields)
- `s2_total_pixels`: Total pixels in the localized AOI patch (e.g. 2,500 for 50×50 at 20m).
- `s2_spectral_valid_pixels`: Number of pixels satisfying valid surface SCL and finite values.
- `s2_spectral_valid_pct`: Percentage of patch pixels used for spectral calculations.
- `s2_feature_status`: `SUCCESS`, `ALL_PIXELS_MASKED`, `MISSING_BAND`, `DIMENSION_MISMATCH`, `EMPTY_PATCH`.
- `s2_feature_failure_reason`: Descriptive error text if feature computation was compromised.

### Spectral Index Statistics (24 fields = 4 indices × 6 statistics)
- **NDVI**: `s2_ndvi_mean`, `s2_ndvi_median`, `s2_ndvi_std`, `s2_ndvi_min`, `s2_ndvi_max`, `s2_ndvi_valid_count`
- **NBR**: `s2_nbr_mean`, `s2_nbr_median`, `s2_nbr_std`, `s2_nbr_min`, `s2_nbr_max`, `s2_nbr_valid_count`
- **NDWI**: `s2_ndwi_mean`, `s2_ndwi_median`, `s2_ndwi_std`, `s2_ndwi_min`, `s2_ndwi_max`, `s2_ndwi_valid_count`
- **SWIR Ratio**: `s2_swir_ratio_mean`, `s2_swir_ratio_median`, `s2_swir_ratio_std`, `s2_swir_ratio_min`, `s2_swir_ratio_max`, `s2_swir_ratio_valid_count`

### Raw Spectral Band Statistics (12 fields = 4 bands × 3 statistics)
- **B04 (Red)**: `s2_b04_mean`, `s2_b04_median`, `s2_b04_std`
- **B08 (NIR)**: `s2_b08_mean`, `s2_b08_median`, `s2_b08_std`
- **B11 (SWIR-1)**: `s2_b11_mean`, `s2_b11_median`, `s2_b11_std`
- **B12 (SWIR-2)**: `s2_b12_mean`, `s2_b12_median`, `s2_b12_std`

---

## 5. Synthetic Demonstration Results

Below is the summary of extracted features across 5 synthetic scenarios:

| Scenario Name | Status | Valid Pixels (%) | NDVI (Mean) | NBR (Mean) | NDWI (Mean) | SWIR Ratio (Mean) | B08 NIR (Mean) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `healthy_vegetation` | `SUCCESS` | 2,500 (100.0%) | 0.627 | 0.589 | 0.370 | 0.564 | 3,499.5 |
| `synthetic_disturbed_ground` | `SUCCESS` | 2,500 (100.0%) | 0.076 | -0.199 | -0.263 | 0.876 | 1,400.9 |
| `partially_cloudy_surface` | `SUCCESS` | 1,750 (70.0%) | 0.473 | 0.366 | 0.217 | 0.723 | 2,802.1 |
| `fully_cloudy_all_masked` | `ALL_PIXELS_MASKED` | 0 (0.0%) | NaN | NaN | NaN | NaN | NaN |
| `missing_band_edge_case` | `MISSING_BAND` | 0 (0.0%) | NaN | NaN | NaN | NaN | NaN |

### Key Observations from the Demonstration
1. **Cloud & Shadow Masking in Action:**
   In `partially_cloudy_surface`, 750 pixels (30%) consisting of clouds (SCL 9) and cloud shadow (SCL 3) were completely masked out. The statistics reflect strictly the remaining 1,750 valid surface pixels without cloud spectral corruption.
2. **Graceful Degeneration:**
   When all pixels are clouds (`fully_cloudy_all_masked`) or when a band is missing (`missing_band_edge_case`), the extractor returns clear diagnostic statuses without raising unhandled exceptions.

---

## 6. Limitations & Path to Step 3B

1. **Optical Surface Constraints:**
   - Sentinel-2 optical reflectance is blocked by opaque clouds. In monsoon periods, local SCL masking ensures invalid observations are flagged rather than producing erroneous spectral values.
2. **Single-Epoch Scope:**
   - Step 3A computes single-patch features. Multi-temporal change analysis (such as pre/post surface disturbance: dNBR and dNDVI) will be implemented in Step 3B.
