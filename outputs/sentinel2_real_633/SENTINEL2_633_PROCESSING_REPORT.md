# Phase 3 — Step 3E: Full-Scale Real Sentinel-2 Processing Report (633 FIRMS Events)

**Component:** `src/feature_engineering/sentinel2_scale_processor.py`  
**Dataset Scope:** 633 authoritative FIRMS thermal events across Tamil Nadu  
**Goal:** Execute verified Sentinel-2 Level-2A data acquisition, GeoTIFF parsing, Step 3A spectral extraction, and Step 3B temporal change calculation across all 633 events.

---

## 1. Executive Summary

Phase 3 Step 3E scales the verified Sentinel-2 pipeline to the complete set of **633 FIRMS events**. This step operates strictly as a **data acquisition and feature extraction layer**:

$$\text{633 FIRMS Events} \longrightarrow \text{CDSE L2A Matcher (disjoint} \pm 15\text{d window)} \longrightarrow \text{Localized 1 km} \times \text{1 km AOI} \longrightarrow \text{Step 3A Spectral Extraction} \longrightarrow \text{Step 3B Pre/Post Change}$$

> [!IMPORTANT]
> **Authentication & Ground-Truth Rules:**
> - **OAuth2 Configuration Status:** `UNCONFIGURED / AUTH_REQUIRED`
> - **Zero Synthetic Fallback:** Synthetic arrays are NEVER substituted as real imagery. When credentials are unconfigured, the pipeline stops safely at the authentication gateway and explicitly records `AUTH_REQUIRED`.
> - **Optical Sensor Constraint:** Sentinel-2 is an optical sensor (VNIR/SWIR), NOT a thermal sensor. Reflectance indices (`dNDVI`, `dNBR`, `dNDWI`, `dSWIR_ratio`) represent optical surface-change evidence only and do NOT prove fire occurrence or active combustion.
> - **Machine Learning Isolation:** Zero machine-learning models were trained, modified, or evaluated in this step.
> - **Phase 2C Datasets Untouched:** The Phase 2C baseline tables and feature pipelines remain 100% unaltered.

---

## 2. Quantitative Processing Metrics

| Metric | Exact Count / Value | Description |
| :--- | :--- | :--- |
| **Total FIRMS Events Processed** | **633** | Exactly 633 unique events from authoritative dataset |
| **Events with Real Pre + Post Imagery** | **0** | Both observations retrieved and change features calculated |
| **Events with Real Pre Only** | **0** | Pre observation retrieved; post unavailable |
| **Events with Real Post Only** | **0** | Post observation retrieved; pre unavailable |
| **Events with Neither Observation** | **633** | Neither pre nor post observation could be retrieved |
| **Total Successful Real Observations** | **0** | Count of individual S2 L2A observations processed |
| **Total Real Pixels Processed** | **0** | (2,500 pixels/observation) |
| **Sentinel-2 Real Data Coverage** | **0.00%** | Ratio of retrieved to possible observation slots (633 x 2 = 1,266) |
| **Total Execution Time** | **1.01 seconds** | End-to-end processing duration |
| **Numerical Candidate Features Produced** | **66** | Step 3A pre/post stats + Step 3B change features |

---

## 3. Status Breakdown Across 633 Events

| Processing Status | Count | Percentage | Operational Meaning |
| :--- | :--- | :--- | :--- |
| `REAL_CDSE_SUCCESS` | 0 | 0.0% | Both pre and post real GeoTIFF rasters successfully processed |
| `PARTIAL_PRE_ONLY` | 0 | 0.0% | Pre observation processed; post unavailable |
| `PARTIAL_POST_ONLY` | 0 | 0.0% | Post observation processed; pre unavailable |
| `AUTH_REQUIRED` | 633 | 100.0% | CDSE credentials not provided; pipeline halted cleanly |
| `CLOUD_REJECTED` | 0 | 0.0% | Real imagery returned but SCL valid surface coverage < 70% |
| `MISSING_PRODUCT` | 0 | 0.0% | Neither pre nor post observation found in catalogue search |
| `PROCESSING_API_ERROR` | 0 | 0.0% | CDSE HTTP timeout or gateway error |
| `PROCESSING_FAILED` | 0 | 0.0% | Corrupt raster bytes or dimension mismatch |

---

## 4. Data Quality and Schema Verification

1. **Row Count Preservation:** Exactly 633 events exist in the output master CSV. No events were dropped.
2. **Event ID Uniqueness:** Every `event_id` is unique (`FIRMS_TN_0000` through `FIRMS_TN_0632`).
3. **Missing Value Integrity:** Unavailable numerical features are explicitly represented as `NaN`, never as fabricated zeros.
4. **Zero Synthetic Intrusion:** When credentials are absent, status is recorded as `AUTH_REQUIRED` without fabricating results.
5. **Zero Credentials Persisted:** No client IDs, secrets, or bearer tokens are stored in the CSV, report, or log files.
6. **Band Integrity:** When real GeoTIFFs are retrieved, all 5 bands (`SCL`, `B04`, `B08`, `B11`, `B12`) are extracted as $50 \times 50$ planes.
7. **SCL Masking:** Step 3A screens valid surface pixels (classes `4`, `5`, `6`) and isolates cloudy/shadow pixels.
8. **Step 3B Gating:** Temporal change features (`dNDVI`, `dNBR`, `dNDWI`, `dSWIR_ratio`) are computed only when both observations are valid.

---

## 5. Phase 2C Integrity Status

- **Phase 2C Datasets:** Completely untouched and intact.
- **FIRMS Data Pipeline:** Unchanged.
- **OSM Retrieval Layer:** Unchanged.
- **WorldCover Land-Cover Sampler:** Unchanged.
- **Machine Learning Models:** Unchanged (no training or re-fitting).
- **Step 3A, 3B, 3C, 3D Components:** Unchanged.

---

## 6. Limitations & Path to Phase 4

1. **Live CDSE Processing:** Full-scale real raster retrieval across 633 events requires active CDSE OAuth2 credentials.
2. **Atmospheric Gaps:** Due to monsoon cloud cover across Tamil Nadu (Nov-Jan), post-event observations have a high cloud-rejection rate in optical imagery.
3. **Evidence Isolation:** Sentinel-2 features will serve as candidate optical features in Phase 4 integration alongside FIRMS, OSM, and WorldCover.