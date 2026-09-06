# Phase 4B: Human Ground-Truth Audit and ML Dataset Preparation Report

**Execution Timestamp:** 2026-09-06 08:09:09Z  
**Validated Input Source:** `outputs/ground_truth_investigation/validation_batch_v1_100_validated.csv`  
**Input SHA256 Checksum:** `1431dc358c97404f9e0ea7d43fc8a7f89fed19f2fecc1f21339afcce4ab3c9fb`  
**Master Dataset Source:** `outputs/phase_4a_dataset_audit/sentinel2_master_633_human_merged.csv`  
**Master SHA256 Checksum:** `f66e6c6f266554a968739c5da2d6c05b61167a7e2242141b2ca56c36f432a184`  
**Audit Status:** COMPLETED — 100 Human Annotations Audited & Integrated  

---

## 1. Executive Summary

Phase 4B performed a comprehensive forensic audit of the completed **100-record human-validated dataset** received from the human review team, normalized the annotations into the project's **six official ground-truth classes**, integrated the verified ground truth into the 633-event master Sentinel-2 dataset, and constructed the clean **ML-ready training dataset**.

### Key Outcomes:
1. **100% of Events Reviewed**: All **100 candidate events** were reviewed by human annotators and marked with `ground_truth_status = VERIFIED`.
2. **Identification of Human Annotation Column**: The human reviewers entered their ground-truth classifications into the column historically titled `weak_label` in the spreadsheet, overwriting the candidate heuristic values with rich domain classifications, detailed typo/case variations, and physical fire/facility descriptions.
3. **Sensor Confidence vs Human Confidence Disentangled**:
   - `confidence` / `confidence_numeric`: NASA VIIRS satellite sensor detection confidence flags (`n` = nominal: 98, `h` = high: 2).
   - `Unnamed: 64`: Human reviewer confidence (recorded for sample events as `high` and `medium`).
   - `Industry `: Specific human observations of physical industrial infrastructure (`Present`: 11, `Absent`: 38, `Present(Sand mining)`: 1).
4. **Normalized Ground Truth**:
   - **76 records** unambiguously mapped to official classes with high confidence.
   - **24 records** placed into `REVIEW_REQUIRED` (annotations prefixed with "possible", non-specific thermal anomalies, or ambiguous brush/waste).
   - **Zero synthetic labels** created or guessed.
5. **Master Dataset Integration**:
   - All 633 events preserved with complete 170+ feature schema.
   - 533 unreviewed master events remain strictly UNLABELED (`ml_training_eligible = False`).
   - Clean ML dataset produced with **76 verified ground-truth instances**.

---

## 2. Audit of Raw Human Annotations (n=100)

- **Total Records:** 100
- **Unique Event IDs:** 100 (0 duplicates, 0 missing)
- **Validation Status:** {"VERIFIED": 36, "verified": 35, "Verified": 28, "veriFIED": 1} (100% verified)
- **Missing Annotations:** 0

### Raw Label Breakdown (27 distinct strings):

| Raw Human Label String | Count | Normalized Official Class | Confidence / Mapping Rationale |
| :--- | :---: | :--- | :--- |
| `Agricultural Burning` | 20 | `Agricultural Burning` | Exact match to Class 3 |
| `agricultural Burning` | 18 | `Agricultural Burning` | Case variation of Class 3 |
| `Persistent Industrial Thermal Source` | 11 | `Persistent Industrial Thermal Source` | Exact match to Class 2 |
| `Natural/Forest Fire` | 7 | `Natural/Forest Fire` | Exact match to Class 4 |
| `Possible Agricultural Burning` | 6 | `REVIEW_REQUIRED` | 'Possible' indicates uncertainty |
| `possible argricultural buring` | 6 | `REVIEW_REQUIRED` | 'Possible' + spelling typo; requires review |
| `agricultural burning` | 5 | `Agricultural Burning` | Case variation of Class 3 |
| `Industrial / Facility Thermal Anomaly` | 3 | `REVIEW_REQUIRED` | Ambiguous between fire vs operational source |
| `Biomass / Agricultural Burning` | 3 | `Agricultural Burning` | Agricultural biomass combustion |
| `Biomass / Scrub Burning` | 2 | `REVIEW_REQUIRED` | Scrub burning crosses Forest/Ag/Other boundaries |
| `industrial/facility fire` | 2 | `Industrial Fire` | Exact match to Class 1 |
| `Other/Unclassified` | 2 | `Other/Unclassified` | Exact match to Class 5 |
| `agriculatural fire` | 1 | `Agricultural Burning` | Typo variation of Class 3 |
| `Presistent Industrial Themal Souce` | 1 | `Persistent Industrial Thermal Source` | Typo variation; Industry = Present |
| `possible forest fire` | 1 | `REVIEW_REQUIRED` | 'Possible' indicates uncertainty |
| `agricultural burn.` | 1 | `Agricultural Burning` | Abbreviation of Class 3 |
| ` Agricultural Burning` | 1 | `Agricultural Burning` | Whitespace variation of Class 3 |
| `argricultural burning` | 1 | `Agricultural Burning` | Typo variation of Class 3 |
| `possible garbage burning` | 1 | `REVIEW_REQUIRED` | 'Possible' indicates uncertainty |
| `Industrial / Facility Fire` | 1 | `Industrial Fire` | Exact match to Class 1 |
| `open brush/waste burning` | 1 | `REVIEW_REQUIRED` | Ambiguous between Other vs Ag vs Forest |
| `NAtural/Forest Fire` | 1 | `Natural/Forest Fire` | Case variation of Class 4 |
| `Industrial Facility` | 1 | `REVIEW_REQUIRED` | Facility present, but fire vs ops unspecified |
| `Industrial Facility / Boiler Anomaly` | 1 | `REVIEW_REQUIRED` | Equipment anomaly; fire vs ops unspecified |
| `Industrial Facility / Salt Refinery` | 1 | `REVIEW_REQUIRED` | Facility present, but fire vs ops unspecified |
| `forest fire` | 1 | `Natural/Forest Fire` | Synonym for Class 4 |
| `possible agricultural Burning` | 1 | `REVIEW_REQUIRED` | 'Possible' indicates uncertainty |

---

## 3. Normalized Six-Class Distribution

### Distribution Across All 100 Reviewed Records:

| Official Class / Status | Count | % of Reviewed Batch | Usable for Supervised ML? |
| :--- | :---: | :---: | :---: |
| **Agricultural Burning** | **50** | 50.0% | **YES** |
| **Persistent Industrial Thermal Source** | **12** | 12.0% | **YES** |
| **Natural/Forest Fire** | **9** | 9.0% | **YES** |
| **Industrial Fire** | **3** | 3.0% | **YES** |
| **Other/Unclassified** | **2** | 2.0% | **YES** |
| **Unknown/Insufficient Evidence** | **0** | 0.0% | N/A (None explicit) |
| *Subtotal (Clean Usable Ground Truth)* | *76* | *76.0%* | *Ready for Training* |
| **REVIEW_REQUIRED (Ambiguous / Possible)** | **24** | 24.0% | **NO (Held out until review)** |
| **Total** | **100** | **100.0%** | |

### Usable ML Training Cohort Breakdown (n=76):
- **Largest Class:** `Agricultural Burning` (50 records, 65.8%)
- **Smallest Class:** `Other/Unclassified` (2 records, 2.6%)
- **Industrial Fire Representation:** Only **3 records** (3.9% of usable dataset)
- **Class Imbalance Ratio:** **25.0 : 1** (50 vs 2)

---

## 4. Analysis of the 24 Records Requiring Review

The 24 records held out under `REVIEW_REQUIRED` fall into three distinct categories:
1. **Uncertain Agricultural / Stubble Labels (13 records):**
   Annotated as `'Possible Agricultural Burning'` or typo `'possible argricultural buring'`. The human reviewer noted uncertainty, meaning these could either be legitimate agricultural burns or unconfirmable events (`Unknown/Insufficient Evidence`).
2. **Uncertain Industrial Thermal Anomalies (6 records):**
   Annotated as `'Industrial / Facility Thermal Anomaly'` (3), `'Industrial Facility'` (1), `'Industrial Facility / Boiler Anomaly'` (1), or `'Industrial Facility / Salt Refinery'` (1). These establish industrial facility presence but do not resolve whether the thermal emission was an accidental fire or operational heat.
3. **Ambiguous Waste / Brush / Forest Detections (5 records):**
   Annotated as `'Biomass / Scrub Burning'` (2), `'possible forest fire'` (1), `'open brush/waste burning'` (1), or `'possible garbage burning'` (1).

Holding these 24 records out prevents noisy or unverified labels from corrupting model training.

---

## 5. Strategic Machine Learning Recommendation

### Question: Is a six-class supervised model statistically reasonable with only 100 labelled records?

> [!CAUTION]
> **Definitive Answer: NO.**  
> Attempting to train a 6-class supervised classifier on this dataset is statistically invalid and practically unfeasible for the following reasons:
> 1. **Extreme Sample Scarcity in Minority Classes**:
>    - `Industrial Fire`: **3 instances**
>    - `Other/Unclassified`: **2 instances**
>    - `Natural/Forest Fire`: **9 instances**
> 2. **Cross-Validation Impossibility**: Standard 5-fold cross-validation requires at least 5 instances per class to have even 1 test sample per fold. With 3 samples, stratified folds cannot be constructed.
> 3. **Massive Class Imbalance**: 50 of the 76 usable records (65.8%) are Agricultural Burning. A naive model predicting Agricultural Burning for all inputs achieves ~66% accuracy while completely failing to detect industrial events.

### Recommended Modeling Formulation:
To maximize scientific validity and utility for the Smart India Hackathon problem statement, we strongly recommend:

1. **Option A (Recommended): 3-Class Coarse Architecture**:
   - **Class 1: Industrial Events** (combining `Industrial Fire` + `Persistent Industrial Thermal Source` = 15 samples, expandable to 21 if ambiguous industrial anomalies are confirmed).
   - **Class 2: Agricultural Burning** (50 samples).
   - **Class 3: Natural & Other** (`Natural/Forest Fire` + `Other/Unclassified` = 11 samples).
   - *Advantage*: Balances the dataset to ~15 vs 50 vs 11, making stratified cross-validation and meaningful F1 evaluation feasible.

2. **Option B: Binary Industrial Detection**:
   - **Positive Class:** Industrial (`Industrial Fire` + `Persistent Source` = 15 samples).
   - **Negative Class:** Non-Industrial (Agricultural + Natural + Other = 61 samples).
   - *Advantage*: Directly answers the core SIH operational question: *"Is this thermal anomaly industrial?"*

---

## 6. Output Artifacts and Data Hygiene

1. **Audited 100 Validation Records:**  
   `outputs/phase_4b_ground_truth/human_validation_audited_100.csv` (100 rows, contains original fields, raw label, normalized class, confidence, industry flag, and review notes).
2. **Master Dataset Integrated:**  
   `outputs/phase_4b_ground_truth/sentinel2_master_633_human_ground_truth.csv` (633 rows, 175 columns).
3. **ML-Ready Clean Dataset:**  
   `outputs/phase_4b_ground_truth/ml_labelled_dataset.csv` (76 rows, strictly unambiguous ground truth).
4. **Source Integrity:** Verified unchanged via SHA256 pre- and post-execution checks.
