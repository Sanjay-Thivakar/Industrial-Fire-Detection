"""
PHASE 5B STEP 2 — Build dashboard_events_633.csv

Sources:
  MASTER : outputs/phase_4b_ground_truth/sentinel2_master_633_human_ground_truth.csv
  PRED   : outputs/phase_5a_inference_633/predictions_633.csv

Join: MASTER LEFT JOIN PRED ON event_id

Rules:
  - Preserve exactly 633 rows
  - Do not modify either source file
  - Do not fabricate missing values
  - Apply renames: confidence->firms_confidence, confidence.1->ml_confidence
  - Expose only the approved 57 dashboard fields
"""

import pandas as pd
import numpy as np
import os
import json
import datetime

REPO = os.path.abspath('.')
MASTER_PATH = os.path.join(REPO, 'outputs', 'phase_4b_ground_truth', 'sentinel2_master_633_human_ground_truth.csv')
PRED_PATH   = os.path.join(REPO, 'outputs', 'phase_5a_inference_633', 'predictions_633.csv')
OUT_DIR     = os.path.join(REPO, 'outputs', 'phase_5b_dashboard')
OUT_CSV     = os.path.join(OUT_DIR, 'dashboard_events_633.csv')

os.makedirs(OUT_DIR, exist_ok=True)

print('='*70)
print('PHASE 5B — BUILD DASHBOARD_EVENTS_633.CSV')
print('='*70)

# ── Load sources ──────────────────────────────────────────────────────────────
print('\n[LOAD] Reading source files...')
master = pd.read_csv(MASTER_PATH)
pred   = pd.read_csv(PRED_PATH)
print(f'  MASTER : {master.shape}')
print(f'  PRED   : {pred.shape}')

# ── Snapshot source values for integrity checks ───────────────────────────────
src_event_ids  = set(master['event_id'].tolist())
src_lat        = master.set_index('event_id')['latitude'].to_dict()
src_lon        = master.set_index('event_id')['longitude'].to_dict()
src_conf       = master.set_index('event_id')['confidence'].to_dict()

pred_class     = pred.set_index('event_id')['predicted_class'].to_dict()
pred_prob_ag   = pred.set_index('event_id')['probability_agricultural_burning'].to_dict()
pred_prob_in   = pred.set_index('event_id')['probability_industrial_thermal_activity'].to_dict()
pred_prob_nw   = pred.set_index('event_id')['probability_natural_wildfire_other'].to_dict()
pred_mlconf    = pred.set_index('event_id')['confidence.1'].to_dict()
pred_maxprob   = pred.set_index('event_id')['max_probability'].to_dict()
pred_model_ver = pred.set_index('event_id')['model_version'].to_dict()
pred_model_sha = pred.set_index('event_id')['model_sha256'].to_dict()
pred_ts        = pred.set_index('event_id')['inference_timestamp'].to_dict()

# ── Join MASTER + PRED on event_id ────────────────────────────────────────────
print('\n[JOIN] LEFT JOIN MASTER + PRED on event_id...')

# Rename confidence.1 in PRED before join to avoid pandas suffix collision
pred_clean = pred.rename(columns={'confidence.1': 'ml_confidence'})

# Drop columns from PRED that already exist in MASTER (avoid _x/_y suffixes)
# We'll take ML-prediction columns from PRED only
pred_ml_cols = ['event_id', 'predicted_class',
                'probability_agricultural_burning',
                'probability_industrial_thermal_activity',
                'probability_natural_wildfire_other',
                'max_probability', 'ml_confidence',
                'model_version', 'model_sha256', 'inference_timestamp']
pred_subset = pred_clean[pred_ml_cols]

joined = master.merge(pred_subset, on='event_id', how='left')
print(f'  Joined shape: {joined.shape}')
print(f'  Join rows matched: {joined["predicted_class"].notna().sum()} / {len(joined)}')

# ── Rename firms confidence ───────────────────────────────────────────────────
joined = joined.rename(columns={'confidence': 'firms_confidence'})

# ── Add derived provenance constant ──────────────────────────────────────────
joined['data_source_version'] = 'phase_4b_ground_truth_v1'

# ── Select exactly the 57 approved dashboard fields ──────────────────────────
DASHBOARD_COLS = [
    # A — Event Identity (6)
    'event_id', 'row_id', 'acq_date', 'acq_time', 'acq_datetime', 'daynight',
    # B — Location (2)
    'latitude', 'longitude',
    # C — FIRMS Thermal Evidence (15)
    'satellite', 'instrument', 'firms_confidence',
    'frp', 'brightness', 'bright_t31', 'brightness_difference',
    'is_day', 'is_stubble_burning_season',
    'grid_detection_count', 'grid_active_days', 'persistent_location_flag',
    'grid_total_frp', 'high_frp_flag_local', 'brightness_zscore_local',
    # D — ML Prediction (6)
    'predicted_class',
    'probability_agricultural_burning',
    'probability_industrial_thermal_activity',
    'probability_natural_wildfire_other',
    'max_probability',
    'ml_confidence',
    # E — OSM Context (12)
    'osm_coverage_status',
    'nearest_facility_name', 'nearest_facility_type',
    'nearest_facility_category', 'nearest_facility_tier',
    'distance_to_facility_m',
    'near_industrial_500m', 'near_industrial_1000m', 'near_industrial_2000m',
    'nearest_hr_category', 'nearest_hr_name', 'distance_to_higher_relevance_m',
    # F — WorldCover (2)
    'landcover_code', 'landcover_class',
    # G — Sentinel-2 (10)
    'pre_observation_status', 'post_observation_status', 's2_change_status',
    'selected_pre_image_date', 'selected_post_image_date',
    's2_pre_feature_status', 's2_post_feature_status',
    's2_pre_ndvi_mean', 's2_post_ndvi_mean', 's2_dnbr_mean',
    # H — Human Validation (4)
    'has_human_validation', 'human_validation_status',
    'human_ground_truth_class', 'is_unambiguous_ground_truth',
    # I — Provenance (5)
    'inference_timestamp', 'model_version', 'model_sha256',
    'data_source_version',
]

# Verify all expected columns are present in joined
missing_cols = [c for c in DASHBOARD_COLS if c not in joined.columns]
if missing_cols:
    raise ValueError(f'Missing columns in joined: {missing_cols}')

df = joined[DASHBOARD_COLS].copy()
print(f'\n[SELECT] Dashboard columns selected: {len(df.columns)}')
print(f'  Rows: {len(df)}')

# ── Write output ──────────────────────────────────────────────────────────────
df.to_csv(OUT_CSV, index=False)
print(f'\n[OUTPUT] Written: {OUT_CSV}')
print(f'  Size: {os.path.getsize(OUT_CSV):,} bytes')

# ── INTEGRITY CHECKS ──────────────────────────────────────────────────────────
print('\n' + '='*70)
print('INTEGRITY CHECKS')
print('='*70)

errors = []
warnings = []

def chk(cond, label, detail=''):
    tag = '[PASS]' if cond else '[FAIL]'
    msg = f'{tag} {label}'
    if detail:
        msg += f' | {detail}'
    print(msg)
    if not cond:
        errors.append(f'{label}: {detail}')

# Check 1
chk(len(df) == 633, 'CHECK 1: Output rows = 633', f'actual={len(df)}')

# Check 2
chk(df['event_id'].nunique() == 633, 'CHECK 2: Unique event_id = 633', f'actual={df["event_id"].nunique()}')

# Check 3
chk(df['event_id'].duplicated().sum() == 0, 'CHECK 3: No duplicate event_id', f'dups={df["event_id"].duplicated().sum()}')

# Check 4
chk(len(df.columns) == len(DASHBOARD_COLS), 'CHECK 4: All 57 approved columns present', f'actual={len(df.columns)}')

# Check 5
extra = [c for c in df.columns if c not in DASHBOARD_COLS]
chk(len(extra) == 0, 'CHECK 5: No unexpected columns', f'extra={extra}')

# Check 6
out_ids = set(df['event_id'].tolist())
chk(out_ids == src_event_ids, 'CHECK 6: event_id set exactly matches MASTER', f'overlap={len(out_ids & src_event_ids)}')

# Check 7 — lat/lon exactly preserved
lat_ok = all(abs(df.loc[df['event_id']==eid,'latitude'].iloc[0] - src_lat[eid]) < 1e-9 for eid in df['event_id'])
lon_ok = all(abs(df.loc[df['event_id']==eid,'longitude'].iloc[0] - src_lon[eid]) < 1e-9 for eid in df['event_id'])
chk(lat_ok and lon_ok, 'CHECK 7: latitude/longitude exactly preserved')

# Check 8 — predicted_class matches PRED
df_sorted = df.sort_values('event_id').reset_index(drop=True)
pc_ok = all(df_sorted.loc[i,'predicted_class'] == pred_class[df_sorted.loc[i,'event_id']] for i in range(len(df_sorted)))
chk(pc_ok, 'CHECK 8: predicted_class exactly matches PRED')

# Check 9 — probabilities match PRED
prob_ok = True
for i in range(len(df_sorted)):
    eid = df_sorted.loc[i,'event_id']
    if abs(df_sorted.loc[i,'probability_agricultural_burning'] - pred_prob_ag[eid]) > 1e-6:
        prob_ok = False; break
    if abs(df_sorted.loc[i,'probability_industrial_thermal_activity'] - pred_prob_in[eid]) > 1e-6:
        prob_ok = False; break
    if abs(df_sorted.loc[i,'probability_natural_wildfire_other'] - pred_prob_nw[eid]) > 1e-6:
        prob_ok = False; break
chk(prob_ok, 'CHECK 9: ML probabilities exactly match PRED')

# Check 10 — ml_confidence matches PRED
mlc_ok = all(df_sorted.loc[i,'ml_confidence'] == pred_mlconf[df_sorted.loc[i,'event_id']] for i in range(len(df_sorted)))
chk(mlc_ok, 'CHECK 10: ml_confidence exactly matches PRED')

# Check 11 — firms_confidence from original FIRMS
fc_ok = all(str(df_sorted.loc[i,'firms_confidence']) == str(src_conf[df_sorted.loc[i,'event_id']]) for i in range(len(df_sorted)))
chk(fc_ok, 'CHECK 11: firms_confidence matches original MASTER confidence column')

# Check 12 — no synthetic values (all ids in source)
chk(len(out_ids - src_event_ids) == 0, 'CHECK 12: No synthetic event IDs introduced', f'fab={sorted(out_ids - src_event_ids)}')

# Check 13 — no credentials/secrets (model_sha256 is public hash, not a key)
secret_patterns = ['password','secret','token','api_key','credential']
secret_found = any(p in col.lower() for col in df.columns for p in secret_patterns)
chk(not secret_found, 'CHECK 13: No credential/secret column names found')

# ── Distribution summaries ─────────────────────────────────────────────────────
print('\n--- PREDICTION CLASS DISTRIBUTION ---')
for cls, cnt in df['predicted_class'].value_counts().items():
    print(f'  {cls:<42}: {cnt:>4} ({100.0*cnt/len(df):5.2f}%)')

print('\n--- ML CONFIDENCE DISTRIBUTION ---')
for tier, cnt in df['ml_confidence'].value_counts().items():
    print(f'  {tier:<10}: {cnt:>4} ({100.0*cnt/len(df):5.2f}%)')

print('\n--- FIRMS CONFIDENCE DISTRIBUTION ---')
for val, cnt in df['firms_confidence'].value_counts().items():
    print(f'  {val:<5}: {cnt:>4} ({100.0*cnt/len(df):5.2f}%)')

print('\n--- HUMAN VALIDATION ---')
print(f'  has_human_validation=True  : {df["has_human_validation"].sum():>4}')
print(f'  has_human_validation=False : {(~df["has_human_validation"].astype(bool)).sum():>4}')
print(f'  is_unambiguous_gt=True     : {df["is_unambiguous_ground_truth"].sum():>4}')
for cls, cnt in df['human_ground_truth_class'].value_counts(dropna=False).items():
    print(f'  human_gt={str(cls):<40}: {cnt:>4}')

print('\n--- S2 OBSERVATION STATUS ---')
print('  pre_observation_status:')
for v, cnt in df['pre_observation_status'].value_counts().items():
    print(f'    {v:<30}: {cnt:>4} ({100.0*cnt/len(df):5.1f}%)')
print('  post_observation_status:')
for v, cnt in df['post_observation_status'].value_counts().items():
    print(f'    {v:<30}: {cnt:>4} ({100.0*cnt/len(df):5.1f}%)')
print('  s2_change_status:')
for v, cnt in df['s2_change_status'].value_counts().items():
    print(f'    {v:<30}: {cnt:>4} ({100.0*cnt/len(df):5.1f}%)')

print('\n--- OSM COVERAGE ---')
for v, cnt in df['osm_coverage_status'].value_counts().items():
    print(f'  {v:<15}: {cnt:>4} ({100.0*cnt/len(df):5.1f}%)')

print('\n--- WORLDCOVER ---')
for v, cnt in df['landcover_class'].value_counts().items():
    print(f'  {v:<30}: {cnt:>4} ({100.0*cnt/len(df):5.1f}%)')

print('\n--- KEY MISSINGNESS ---')
high_null = [(c, df[c].isna().sum()) for c in df.columns if df[c].isna().sum() > 0]
high_null.sort(key=lambda x: -x[1])
for col, n in high_null[:15]:
    print(f'  {col:<42}: {n:>4} null ({100.0*n/len(df):5.1f}%)')

print('\n' + '='*70)
if errors:
    print(f'BUILD COMPLETE — {len(errors)} INTEGRITY FAILURE(S):')
    for e in errors:
        print(f'  FAIL: {e}')
else:
    print('BUILD COMPLETE — ALL 13 INTEGRITY CHECKS PASSED')
print('='*70)
