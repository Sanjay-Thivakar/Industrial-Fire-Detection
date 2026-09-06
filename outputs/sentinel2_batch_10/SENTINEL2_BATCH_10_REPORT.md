# Sentinel-2 Real-Processing Validation Batch Report (10 Events)

## Executive Summary

- **Total Events Attempted:** `10`
- **Real CDSE Successes (Full Pre & Post):** `2`
- **Partial Success (Pre-only):** `3`
- **Partial Success (Post-only):** `1`
- **Total Events with Real CDSE Data:** `10`
- **Real Sentinel-2 Coverage Rate:** `100.0%`
- **Missing Pre-event Observations:** `1`
- **Missing Post-event Observations:** `4`
- **Missing Both Pre & Post:** `0`
- **Insufficient Valid Data (Cloud/Shadow Rejected):** `4` (Pre: 4, Post: 3)
- **Authentication / API Failures:** `0` (Auth: 0, API: 0)
- **Other Failures:** `0`
- **Successfully Calculated Single-Observation Feature Sets:** `13`
- **Successfully Calculated Temporal Change Sets (Step 3B):** `2`
- **Sentinel-2 Observation Date Range:** `2024-10-29 to 2025-01-04`
- **Total Batch Runtime:** `83.76 seconds`

## Per-Event Results Table

| Event ID | Priority | Land Cover | FRP (MW) | Event Date | Pre Date | Pre Status | Post Date | Post Status | Overall Status | Real CDSE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FIRMS_TN_0007` | HIGH | Built-up | 1.23 | 2024-11-04 | 2024-10-29 | `REAL_CDSE_SUCCESS` | 2024-11-10 | `REAL_CDSE_SUCCESS` | `REAL_CDSE_SUCCESS` | YES |
| `FIRMS_TN_0087` | HIGH | Cropland | 1.08 | 2024-12-04 | None | `MISSING_PRODUCT` | 2024-12-08 | `CLOUD_REJECTED` | `CLOUD_REJECTED` | YES |
| `FIRMS_TN_0001` | HIGH | Tree cover | 5.15 | 2024-11-02 | 2024-10-31 | `CLOUD_REJECTED` | 2024-11-05 | `REAL_CDSE_SUCCESS` | `PARTIAL_POST_ONLY` | YES |
| `FIRMS_TN_0297` | HIGH | Tree cover | 13.34 | 2025-01-08 | 2025-01-04 | `REAL_CDSE_SUCCESS` | None | `MISSING_PRODUCT` | `PARTIAL_PRE_ONLY` | YES |
| `FIRMS_TN_0000` | MEDIUM | Built-up | 1.16 | 2024-11-01 | 2024-10-29 | `REAL_CDSE_SUCCESS` | None | `MISSING_PRODUCT` | `PARTIAL_PRE_ONLY` | YES |
| `FIRMS_TN_0004` | MEDIUM | Cropland | 4.01 | 2024-11-04 | 2024-10-31 | `REAL_CDSE_SUCCESS` | 2024-11-05 | `REAL_CDSE_SUCCESS` | `REAL_CDSE_SUCCESS` | YES |
| `FIRMS_TN_0046` | MEDIUM | Tree cover | 8.09 | 2024-11-10 | 2024-11-05 | `REAL_CDSE_SUCCESS` | None | `MISSING_PRODUCT` | `PARTIAL_PRE_ONLY` | YES |
| `FIRMS_TN_0017` | MEDIUM | Shrubland | 1.09 | 2024-11-05 | 2024-10-31 | `CLOUD_REJECTED` | 2024-11-10 | `CLOUD_REJECTED` | `CLOUD_REJECTED` | YES |
| `FIRMS_TN_0038` | LOW | Cropland | 2.37 | 2024-11-09 | 2024-11-08 | `CLOUD_REJECTED` | None | `MISSING_PRODUCT` | `CLOUD_REJECTED` | YES |
| `FIRMS_TN_0002` | LOW | Shrubland | 2.77 | 2024-11-03 | 2024-10-29 | `CLOUD_REJECTED` | 2024-11-05 | `CLOUD_REJECTED` | `CLOUD_REJECTED` | YES |

## Quality and Science Verification

1. **Optical vs Thermal Constraint:** Sentinel-2 Level-2A data measures surface reflectance (VNIR/SWIR) and SCL ground quality. It is strictly optical and does not measure active fire heat.
2. **Zero Synthetic Substitution:** No synthetic or surrogate pixels were substituted for missing or cloud-obscured observations.
3. **Strict Credential Masking:** No client credentials or access tokens were logged or persisted.
