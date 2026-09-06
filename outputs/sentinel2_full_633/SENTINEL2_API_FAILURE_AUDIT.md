# Sentinel-2 Full 633-Event Processing API Failure Audit

## 1. Executive Summary

During the full 633-event Sentinel-2 processing run, **241 events** were categorized with status `PROCESSING_API_ERROR`. A strict forensic audit of the execution manifest, master dataset, and cache checkpoints was performed to determine the root cause, distinguish technical failures from legitimate outcomes, and establish the exact retry requirements.

> [!IMPORTANT]
> **Root Cause Identified: OAuth2 Access Token Expiration**
> - **Failure Mechanism:** The continuous 633-event execution ran for **50.62 minutes**. The Copernicus Data Space Ecosystem (CDSE) >   OAuth2 bearer token has a standard expiration lifetime (10-30 minutes). Once expired, subsequent requests to the Sentinel Hub >   Processing API endpoint returned `HTTP 401: AccessToken signature expired`.
> - **Technical vs Legitimate Distinction:** All 241 events failed exclusively due to this transient token expiration. >   Legitimate outcomes (`MISSING_PRODUCT`, `CLOUD_REJECTED`) were preserved without false positive technical error categorization.
> - **Zero Data Fabrication:** No synthetic pixels or surrogate observations were substituted.

---

## 2. Quantitative Failure & Retry Breakdown

| Metric | Count | Description |
| :--- | :---: | :--- |
| **Total API Failure Events Audited** | **`241`** | All events with overall status `PROCESSING_API_ERROR` |
| **Events Requiring Both Pre & Post Retry** | **`115`** | Both pre and post observation windows experienced HTTP 401 token expiry |
| **Events Requiring Pre Retry Only** | **`62`** | Pre window experienced HTTP 401; post window is legitimately `MISSING_PRODUCT` |
| **Events Requiring Post Retry Only** | **`64`** | Post window experienced HTTP 401; pre window is legitimately `MISSING_PRODUCT` |
| **Events Requiring No Retry** | **`0`** | Events with legitimate non-technical outcomes (0 among the 241) |
| **Total Unique Retryable Events** | **`241`** | Exactly 241 events have at least one retryable window |
| **Total Retryable Pre-Event Windows** | **`177`** | Pre-event observation windows eligible for retry |
| **Total Retryable Post-Event Windows** | **`179`** | Post-event observation windows eligible for retry |
| **Total Retryable Observation Windows** | **`356`** | Combined individual observation windows to be retrieved |

---

## 3. Observation Status Contingency Matrix

| Pre-Event Status | Post-Event Status | Event Count | Retry Eligibility | Target Windows to Retry |
| :--- | :--- | :---: | :--- | :---: |
| `PROCESSING_API_ERROR` | `PROCESSING_API_ERROR` | 115 | Both windows eligible for retry | 230 windows (115 pre + 115 post) |
| `PROCESSING_API_ERROR` | `MISSING_PRODUCT` | 62 | Pre window only (post is legitimate catalogue absence) | 62 windows (pre only) |
| `MISSING_PRODUCT` | `PROCESSING_API_ERROR` | 64 | Post window only (pre is legitimate catalogue absence) | 64 windows (post only) |
| `MISSING_PRODUCT` | `MISSING_PRODUCT` | 0 | None (correctly categorized as `MISSING_PRODUCT`) | 0 |
| **Total** | | **241** | | **356 windows** |

---

## 4. Breakdown of Error Signatures

| Error Signature / Recorded Diagnostic Message | Occurrence Count in Windows | Category |
| :--- | :---: | :--- |
| `HTTP 401: AccessToken signature expired (OAuth2 Token Expiry)` | 356 | Transient Technical (Token Expiration) |
| `Catalogue search: No usable product matched (Legitimate)` | 126 | Legitimate Catalogue Outcome |

---

## 5. Dataset & Consistency Audit

1. **Authoritative Dataset Presence:** All 241 `event_id`s were cross-referenced against `validation_candidates_v2.csv`. Exactly 241 exist, and each exists **exactly once**.
2. **Category Isolation:** Zero events outside the `PROCESSING_API_ERROR` category contained API failure sub-statuses.
3. **Inconsistencies Discovered:** `None. Zero inconsistencies detected.`
4. **Preservation of Legitimate Outcomes:** For the 126 events where one window was legitimately `MISSING_PRODUCT` (64 pre, 62 post), the retry manifest strictly flags only the failed window (`retry_pre=False` or `retry_post=False`), preventing unnecessary queries for non-existent satellite products.

---

## 6. Generated Audit Artifacts

- **Retry Manifest CSV:** [`sentinel2_api_retry_manifest.csv`](file:///c:/Users/sanja/OneDrive/Documents/Sanjay/Colllege_Projects/SIH%20PROJECT/outputs/sentinel2_full_633/sentinel2_api_retry_manifest.csv) (241 rows)
- **Audit Report:** [`SENTINEL2_API_FAILURE_AUDIT.md`](file:///c:/Users/sanja/OneDrive/Documents/Sanjay/Colllege_Projects/SIH%20PROJECT/outputs/sentinel2_full_633/SENTINEL2_API_FAILURE_AUDIT.md)

---

## 7. Recommended Protocol for Subsequent Targeted Retry

1. **Automatic Token Refresh:** Before executing retries, ensure `Sentinel2ProcessingClient` checks token validity or refreshes the token on HTTP 401 responses.
2. **Targeted Window Retrieval:** In the retry step, retrieve ONLY the observation windows flagged `True` in `sentinel2_api_retry_manifest.csv` (356 total windows).
3. **Zero Impact on Succeeded Events:** The 392 non-error events (`REAL_CDSE_SUCCESS`, `PARTIAL_PRE_ONLY`, `PARTIAL_POST_ONLY`, `CLOUD_REJECTED`, `MISSING_PRODUCT`) remain completely untouched.
