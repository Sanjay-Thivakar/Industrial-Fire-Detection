# Phase 3 — Step 3C: Real Sentinel-2 CDSE Processing Report

**Component:** `src/feature_engineering/sentinel2_real_processor.py`  
**Target Dataset:** 10-event prototype from Phase 3 Step 1  
**Scope:** Real Sentinel-2 Level-2A imagery retrieval via CDSE Processing API, Step 3A spectral extraction, and Step 3B change calculation

---

## 1. Executive Summary

Phase 3 Step 3C establishes the connection between the modular Sentinel-2 feature engineering layer and the **Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Processing API**. It processes the 10-event historical prototype through the full pipeline:

$$\text{FIRMS Event} \longrightarrow \text{CDSE Localized AOI (1 km} \times \text{1 km)} \longrightarrow \text{Raw GeoTIFF (SCL, B04, B08, B11, B12)} \longrightarrow \text{Step 3A Spectral Extractor} \longrightarrow \text{Step 3B Change Calculator}$$

> [!IMPORTANT]
> **Authentication and Ground-Truth Protocol:**
> - **OAuth2 Configuration Status:** `UNCONFIGURED / AUTH_REQUIRED`
> - **Zero Synthetic Substitution:** Synthetic imagery is NEVER substituted as a fallback for real imagery. If credentials are not configured, the pipeline halts at authentication and reports `AUTH_REQUIRED` explicitly.
> - **Optical Nature Disclaimer:** Sentinel-2 is an optical sensor (VNIR/SWIR), NOT a thermal sensor. Reflectance indices (`dNDVI`, `dNBR`, `dNDWI`) represent optical surface-change evidence only and do NOT prove fire occurrence or industrial causality.
> - **No Model Modification:** Zero ML models were trained, modified, or evaluated in this step.

---

## 2. Processing Outcome Breakdown (10 Prototype Events)

| Outcome Category | Count | Status Code | Meaning |
| :--- | :--- | :--- | :--- |
| **Real CDSE Processed** | 0 / 10 | `REAL_CDSE_SUCCESS` | Both pre and post real GeoTIFF rasters retrieved and processed |
| **Authentication Required** | 10 / 10 | `AUTH_REQUIRED` | CDSE credentials not provided in environment; pipeline safely stopped |
| **Missing Pre Product** | 0 / 10 | `MISSING_PRE_PRODUCT` | Pre observation unavailable in catalogue search (e.g., persistent cloud) |
| **Missing Post Product** | 0 / 10 | `MISSING_POST_PRODUCT` | Post observation unavailable in catalogue search (cloud > 40%) |
| **Missing Both Products** | 0 / 10 | `MISSING_BOTH_PRODUCTS` | Neither observation passed catalogue screening |
| **Processing API Error** | 0 / 10 | `PROCESSING_API_ERROR` | CDSE server error or HTTP timeout |
| **Other Failures** | 0 / 10 | `PROCESSING_FAILED` | Coordinate, raster corruption, or pipeline error |

---

## 3. Event-by-Event Prototype Status

| Event ID | Priority | Land Cover | Pre Obs Date | Post Obs Date | Processing Status | Change Status | Real CDSE Data | Failure Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FIRMS_TN_0007` | HIGH | Built-up | 2024-10-29 | 2024-11-10 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0087` | HIGH | Cropland | None | 2024-12-08 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0001` | HIGH | Tree cover | 2024-10-31 | 2024-11-05 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0297` | HIGH | Tree cover | 2025-01-04 | None | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0000` | MEDIUM | Built-up | 2024-10-29 | None | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0004` | MEDIUM | Cropland | 2024-10-31 | 2024-11-05 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0046` | MEDIUM | Tree cover | 2024-11-05 | None | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0017` | MEDIUM | Shrubland | 2024-10-31 | 2024-11-10 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0038` | LOW | Cropland | 2024-11-08 | None | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |
| `FIRMS_TN_0002` | LOW | Shrubland | 2024-10-29 | 2024-11-05 | `AUTH_REQUIRED` | `INVALID_INPUT` | NO | CDSE OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLI |

---

## 4. Verification and Validation Criteria

When real CDSE credentials are provided and GeoTIFF raster bytes are returned, the pipeline validates:

1. **Raster Parsing and Dimensions:** Multi-band GeoTIFF is unpacked via `MemoryFile` in `rasterio`. Dimensions are strictly verified to match `50 x 50` pixels (1000m / 20m).
2. **Band Integrity:** All 5 required bands (`SCL`, `B04`, `B08`, `B11`, `B12`) are extracted as separate 2D planes.
3. **Spatial Alignment:** All 5 planes share the exact same spatial grid and bounding box from the Sentinel Hub request.
4. **Finite Values:** Non-finite or invalid values are checked before computing ratios.
5. **SCL Masking:** Step 3A `Sentinel2SpectralExtractor` strictly screens pixels to valid classes (`4, 5, 6`) and masks out clouds, cloud shadows, and defective pixels.
6. **Step 3B Temporal Difference Calculation:** Evaluates `dNDVI`, `dNBR`, `dNDWI`, `dSWIR_ratio` and absolute changes.

---

## 5. Mocked Deterministic Testing

To prevent the test suite from depending on live CDSE server availability or credentials, deterministic unit and integration tests in `tests/test_sentinel2_real_processor.py` verify:
- Synthetic in-memory GeoTIFF bytes generation and parsing.
- Spatial alignment and dimensional compliance.
- Step 3A feature extraction on parsed GeoTIFF arrays.
- Step 3B change calculation on parsed pre and post rasters.
- Graceful handling of unconfigured credentials (`AUTH_REQUIRED`).
- Graceful handling of missing products (`MISSING_PRODUCT`).
- Graceful handling of cloud-obscured patches (`ALL_PIXELS_MASKED`).
- Graceful handling of API errors (HTTP 400/500).

---

## 6. Phase 2C Integrity Verification

- **Phase 2C Files:** Completely untouched and unchanged.
- **FIRMS Data Pipeline:** Unchanged.
- **OSM Pipeline:** Unchanged.
- **WorldCover Pipeline:** Unchanged.
- **ML Models:** Unchanged (no training or feature vector modification).
- **Step 3A / 3B Modules:** Unchanged (clean modular consumers).

---

## 7. Limitations and Operating Constraints

1. **CDSE Credentials:** Real CDSE processing requires `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` configured in the environment.
2. **Cloud Occlusion:** Optical Sentinel-2 imagery cannot penetrate clouds. Missing post observations are expected and handled.
3. **Prototype Scope:** Evaluated strictly on the 10 representative events. Full 633-event scaling is deferred.