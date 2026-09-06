import pandas as pd
import numpy as np
import os
import hashlib

PRED  = "outputs/phase_5a_inference_633/predictions_633.csv"
SRC   = "outputs/phase_4b_ground_truth/sentinel2_master_633_human_ground_truth.csv"
MODEL = "outputs/phase_5_ml_handoff/final_model.joblib"

df  = pd.read_csv(PRED)
src = pd.read_csv(SRC)

prob_cols = [
    "probability_agricultural_burning",
    "probability_industrial_thermal_activity",
    "probability_natural_wildfire_other",
]
approved_classes = {"Agricultural Burning", "Industrial Thermal Activity", "Natural / Wildfire / Other"}

audit = {}

# ============================================================
# CHECK 1 — ROW / ID INTEGRITY
# ============================================================
c1 = {}
c1["row_count"] = len(df)
c1["unique_event_ids"] = int(df["event_id"].nunique())
c1["unique_row_ids"] = int(df["row_id"].nunique())

src_ids = set(src["event_id"].tolist())
out_ids = set(df["event_id"].tolist())
c1["ids_match_source"] = (src_ids == out_ids)
c1["ids_only_in_source"] = sorted(src_ids - out_ids)
c1["ids_only_in_output"] = sorted(out_ids - src_ids)

# lat/lon check via index-aligned comparison (both are ordered 0..632)
src_sorted = src.sort_values("event_id").reset_index(drop=True)
df_sorted  = df.sort_values("event_id").reset_index(drop=True)
lat_diff = (df_sorted["latitude"] - src_sorted["latitude"]).abs().max()
lon_diff = (df_sorted["longitude"] - src_sorted["longitude"]).abs().max()
c1["latitude_max_abs_diff"]  = float(lat_diff)
c1["longitude_max_abs_diff"] = float(lon_diff)
audit["check1"] = c1

# ============================================================
# CHECK 2 — PREDICTION VALIDITY
# ============================================================
c2 = {}
c2["predicted_class_null_count"]  = int(df["predicted_class"].isna().sum())
actual_classes = set(df["predicted_class"].dropna().unique())
c2["actual_classes_found"]  = sorted(actual_classes)
c2["unexpected_classes"]    = sorted(actual_classes - approved_classes)
c2["missing_approved_class"] = sorted(approved_classes - actual_classes)
audit["check2"] = c2

# ============================================================
# CHECK 3 — PROBABILITY VALIDITY
# ============================================================
c3 = {}
for pc in prob_cols:
    s = df[pc]
    c3[pc] = {
        "null_count":  int(s.isna().sum()),
        "inf_count":   int(np.isinf(s.fillna(0)).sum()),
        "below_0":     int((s < 0).sum()),
        "above_1":     int((s > 1).sum()),
        "min":  round(float(s.min()), 6),
        "max":  round(float(s.max()), 6),
        "mean": round(float(s.mean()), 6),
    }
prob_sum = df[prob_cols].sum(axis=1)
c3["prob_sum_min"]           = round(float(prob_sum.min()), 8)
c3["prob_sum_max"]           = round(float(prob_sum.max()), 8)
c3["prob_sum_mean"]          = round(float(prob_sum.mean()), 8)
c3["rows_outside_sum_tol"]   = int(((prob_sum - 1.0).abs() > 0.001).sum())

# argmax verification
col_to_class = {
    "probability_agricultural_burning":      "Agricultural Burning",
    "probability_industrial_thermal_activity": "Industrial Thermal Activity",
    "probability_natural_wildfire_other":    "Natural / Wildfire / Other",
}
argmax_class = df[prob_cols].idxmax(axis=1).map(col_to_class)
mismatch_mask = df["predicted_class"] != argmax_class
c3["argmax_mismatch_count"] = int(mismatch_mask.sum())
if mismatch_mask.sum() > 0:
    c3["argmax_mismatch_sample"] = df.loc[mismatch_mask, ["event_id","predicted_class"]].head(5).to_dict(orient="records")
audit["check3"] = c3

# ============================================================
# CHECK 4 — CONFIDENCE COLUMNS
# ============================================================
c4 = {}
c4["firms_confidence_col"]   = "confidence"
c4["ml_confidence_col"]      = "confidence.1"
c4["firms_description"]      = "Original NASA FIRMS confidence string (n=nominal, h=high, l=low or numeric % string)"
c4["ml_description"]         = "Model prediction confidence tier derived from max class probability: HIGH>=0.75, MEDIUM>=0.50, LOW<0.50"
c4["firms_value_counts"]     = df["confidence"].value_counts().to_dict()
c4["ml_value_counts"]        = df["confidence.1"].value_counts().to_dict()
audit["check4"] = c4

# ============================================================
# CHECK 5 — SOURCE FIELD PRESERVATION
# ============================================================
compare_fields = ["event_id","row_id","latitude","longitude","acq_date","satellite","instrument","frp","brightness","confidence"]
c5 = {}
src_s = src.sort_values("event_id").reset_index(drop=True)
df_s  = df.sort_values("event_id").reset_index(drop=True)

for fld in compare_fields:
    if fld not in df.columns:
        c5[fld] = "MISSING_FROM_OUTPUT"
        continue
    if fld not in src.columns:
        c5[fld] = "MISSING_FROM_SOURCE"
        continue
    a = df_s[fld]
    b = src_s[fld]
    if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
        diff = (a - b).abs().max()
        c5[fld] = {"type":"numeric","max_abs_diff": float(diff)}
    else:
        mismatch_n = (a.astype(str) != b.astype(str)).sum()
        c5[fld] = {"type":"string","mismatch_count": int(mismatch_n)}
audit["check5"] = c5

# ============================================================
# CHECK 6 — MODEL PROVENANCE
# ============================================================
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

c6 = {}
c6["model_path_recorded"]   = df["model_path"].iloc[0]
c6["model_sha256_recorded"]  = df["model_sha256"].iloc[0]
c6["model_sha256_verified"]  = sha256_file(MODEL)
c6["sha256_match"]           = (c6["model_sha256_recorded"] == c6["model_sha256_verified"])
c6["model_version"]          = df["model_version"].iloc[0]
c6["inference_timestamp"]    = df["inference_timestamp"].iloc[0]
c6["model_file_size_bytes"]  = os.path.getsize(MODEL)
c6["required_feature_count"] = 36
c6["unique_model_paths_in_output"] = list(df["model_path"].unique())
c6["unique_model_versions_in_output"] = list(df["model_version"].unique())
c6["unique_timestamps_in_output"] = list(df["inference_timestamp"].unique())
audit["check6"] = c6

# ============================================================
# CHECK 7 — SYNTHETIC / INVALID DATA
# ============================================================
c7 = {}
c7["fabricated_event_ids"]    = sorted(out_ids - src_ids)
c7["events_in_src_not_output"] = sorted(src_ids - out_ids)
c7["predicted_class_null"]    = int(df["predicted_class"].isna().sum())
c7["any_prob_null"]           = int(df[prob_cols].isna().any(axis=1).sum())
c7["any_prob_out_of_range"]   = int(((df[prob_cols] < 0) | (df[prob_cols] > 1)).any(axis=1).sum())
c7["any_prob_inf"]            = int(np.isinf(df[prob_cols].fillna(0)).any(axis=1).sum())
c7["row_count_matches_source"] = (len(df) == len(src))
audit["check7"] = c7

# ============================================================
# CHECK 8 — CLASS DISTRIBUTION
# ============================================================
c8 = {}
total = len(df)
class_vc = df["predicted_class"].value_counts()
c8["class_distribution"] = {
    k: {"count": int(v), "pct": round(100.0*v/total, 2)}
    for k, v in class_vc.items()
}
ml_conf_vc = df["confidence.1"].value_counts()
c8["ml_confidence_distribution"] = {
    k: {"count": int(v), "pct": round(100.0*v/total, 2)}
    for k, v in ml_conf_vc.items()
}
audit["check8"] = c8

# ============================================================
# CHECK 9 — OUTPUT SCHEMA
# ============================================================
c9 = {}
source_cols    = ["event_id","row_id","latitude","longitude","acq_date","acq_time","satellite","satellite_source","instrument","frp","brightness","bright_t31","confidence","daynight","landcover_class","nearest_facility_name","nearest_facility_osm_id","distance_to_facility_m","distance_to_facility_km","candidate_priority"]
ml_pred_cols   = ["predicted_class","probability_agricultural_burning","probability_industrial_thermal_activity","probability_natural_wildfire_other","max_probability","confidence.1"]
prov_cols      = ["model_path","model_sha256","model_version","inference_timestamp"]
ambig_cols     = ["confidence","confidence.1"]
c9["source_columns"]       = source_cols
c9["ml_prediction_columns"] = ml_pred_cols
c9["provenance_columns"]   = prov_cols
c9["ambiguous_columns"]    = ambig_cols
c9["total_column_count"]   = int(len(df.columns))
c9["all_columns"]          = list(df.columns)
audit["check9"] = c9

import json
print(json.dumps(audit, indent=2, default=str))
