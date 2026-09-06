# Phase 3 — Step 3D: CDSE Authentication & Real Sentinel-2 Smoke Test Report

**Component:** `src/feature_engineering/sentinel2_real_smoketest.py`  
**Test Scope:** 4 representative FIRMS prototype events  
**Goal:** Prove secure CDSE OAuth2 authentication, real L2A localized GeoTIFF raster access, Step 3A spectral feature extraction, and Step 3B temporal change calculation on actual CDSE pixels.

---

## 1. Executive Summary

Phase 3 Step 3D implements the real-world operational smoke test connecting the Sentinel-2 feature engineering layer directly to the **Copernicus Data Space Ecosystem (CDSE)** Processing API. The smoke test was executed against a focused subset of representative FIRMS prototype events.

> [!IMPORTANT]
> **Authentication & Ground-Truth Protocol:**
> - **OAuth2 Credentials Status:** `UNCONFIGURED / AUTH_REQUIRED`
> - **No Synthetic Substitution:** Zero synthetic arrays are used as fallbacks for real processing. If credentials are unconfigured, the live runner halts safely at authentication.
> - **Optical Sensor Constraint:** Sentinel-2 measures optical surface reflectance (VNIR/SWIR), NOT thermal heat. It cannot observe combustion flames or thermal plumes. Change features represent optical surface-change evidence only and do not prove fire or industrial causality.
> - **No Machine Learning Alteration:** Zero ML models were trained or modified.

---

## 2. Smoke Test Execution Breakdown

| Status Category | Count | Status Code | Meaning |
| :--- | :--- | :--- | :--- |
| **Real CDSE Processed** | 0 / 4 | `REAL_CDSE_SUCCESS` | Real GeoTIFF received, parsed, and successfully processed through Step 3A & 3B |
| **Authentication Required** | 4 / 4 | `AUTH_REQUIRED` | CDSE credentials not provided; pipeline halted cleanly at auth gateway |
| **Cloud Rejected** | 0 / 4 | `CLOUD_REJECTED` | Real imagery returned but SCL screening found valid surface coverage < 70% |
| **Missing Pre Product** | 0 / 4 | `MISSING_PRE_PRODUCT` | Pre-event observation unavailable in catalogue search |
| **Missing Post Product** | 0 / 4 | `MISSING_POST_PRODUCT` | Post-event observation unavailable in catalogue search |
| **Missing Both Products** | 0 / 4 | `MISSING_BOTH_PRODUCTS` | Neither observation passed catalogue cloud screening |
| **Processing API Error** | 0 / 4 | `PROCESSING_API_ERROR` | CDSE HTTP request timeout or server error |
| **Processing Failed** | 0 / 4 | `PROCESSING_FAILED` | Corrupt raster bytes, coordinate errors, or dimension mismatch |

---

## 3. Event-by-Event Smoke Test Results

| Event ID | Priority | Land Cover | Pre Date | Post Date | Smoke Test Status | Change Status | Real CDSE Data | Failure / Diagnostic Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FIRMS_TN_0007` | HIGH | Built-up | 2024-10-29 | 2024-11-10 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLIENT_S |
| `FIRMS_TN_0087` | HIGH | Cropland | None | 2024-12-08 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLIENT_S |
| `FIRMS_TN_0001` | HIGH | Tree cover | 2024-10-31 | 2024-11-05 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLIENT_S |
| `FIRMS_TN_0297` | HIGH | Tree cover | 2025-01-04 | None | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLIENT_S |

---

## 4. Successful Event Verification Criteria

For every observation successfully retrieved and processed via CDSE, the pipeline rigorously verifies:

1. **Bands Present:** Multi-band GeoTIFF contains `SCL`, `B04`, `B08`, `B11`, and `B12` in expected order.
2. **Spatial Dimensions and Grid:** Raster dimensions strictly match `50 x 50` pixels at 20 m resolution on WGS84 localized AOI.
3. **Finite Pixel Reflectance:** Array values are non-negative and finite.
4. **Granular SCL Masking:** Step 3A screens valid surface pixels (classes `4`, `5`, `6`) and isolates cloudy/shadow pixels.
5. **Step 3A Spectral Output:** Computes pixel-level summary statistics (`mean`, `median`, `std`) for `NDVI`, `NBR`, `NDWI`, and `SWIR_ratio`.
6. **Step 3B Change Output:** Computes temporal pre/post differences (`dNDVI`, `dNBR`, `dNDWI`, `dSWIR_ratio`) and absolute changes.

---

## 5. Mocked Deterministic Test Coverage

Deterministic tests in `tests/test_sentinel2_smoketest.py` isolate network dependencies via mocked HTTP responses:
- Verified CDSE OAuth2 token exchange and token caching.
- Verified multi-band GeoTIFF byte construction and unpacking.
- Verified Step 3A spectral extraction on parsed GeoTIFF arrays.
- Verified Step 3B change calculation across pre and post rasters.
- Verified handling of missing credentials (`AUTH_REQUIRED`).
- Verified handling of cloud-obscured patches (`CLOUD_REJECTED`).
- Verified handling of HTTP 401/403/500 API errors (`PROCESSING_API_ERROR`).

---

## 6. Phase 2C Integrity Verification

- **Phase 2C Files:** Completely untouched and unchanged.
- **FIRMS Data Pipeline:** Unchanged.
- **OSM Pipeline:** Unchanged.
- **WorldCover Pipeline:** Unchanged.
- **ML Models:** Unchanged (no training, evaluation, or vector modification).
- **Step 3A / 3B Modules:** Unchanged.

---

## 7. Operating Limitations & Next Steps

1. **Authentication Requirement:** Real Sentinel-2 processing requires valid CDSE OAuth2 client credentials.
2. **Atmospheric Limitations:** Optical sensors cannot see through clouds; missing post observations must be handled gracefully.
3. **Scope Control:** Executed strictly on the focused prototype subset. 633-event scaling remains unexecuted.