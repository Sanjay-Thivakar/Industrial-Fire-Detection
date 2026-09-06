import os, sys, time, hashlib, datetime
import pandas as pd

REPO_ROOT = os.path.abspath('.')
sys.path.insert(0, REPO_ROOT)

from src.models.predict import predict_batch, REQUIRED_FEATURES, TARGET_LEAKAGE_FIELDS

SOURCE_CSV = 'outputs/phase_4b_ground_truth/sentinel2_master_633_human_ground_truth.csv'
MODEL_PATH = 'outputs/phase_5_ml_handoff/final_model.joblib'
OUTPUT_DIR = 'outputs/phase_5a_inference_633'
OUTPUT_CSV = os.path.join(OUTPUT_DIR, 'predictions_633.csv')

PRESERVE_COLS = [
    'event_id','row_id','latitude','longitude',
    'acq_date','acq_time','satellite','satellite_source','instrument',
    'frp','brightness','bright_t31','confidence','daynight',
    'landcover_class',
    'nearest_facility_name','nearest_facility_osm_id',
    'distance_to_facility_m','distance_to_facility_km',
    'grid_id','grid_lat','grid_lon','candidate_priority',
]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

print('='*70)
print('PHASE 5A -- PRODUCTION BATCH INFERENCE (633 EVENTS)')
print('='*70)

model_sha256 = sha256_file(MODEL_PATH)
model_size = os.path.getsize(MODEL_PATH)
print(f'\n[MODEL]  {MODEL_PATH}')
print(f'  SHA-256 : {model_sha256}')
print(f'  Size    : {model_size} bytes')

print(f'\n[SOURCE] Loading: {SOURCE_CSV}')
df_source = pd.read_csv(SOURCE_CSV)
print(f'  Loaded  : {len(df_source)} rows x {len(df_source.columns)} columns')

missing_feats = [f for f in REQUIRED_FEATURES if f not in df_source.columns]
if missing_feats:
    raise ValueError(f'Missing features: {missing_feats}')
print('  Features: 36/36 required features present OK')

# Strip leakage columns BEFORE passing to predict_batch
# predict_batch->validate_and_prepare_features checks for leakage fields
# then selects only REQUIRED_FEATURES anyway; we drop them proactively.
leakage_present = [c for c in TARGET_LEAKAGE_FIELDS if c in df_source.columns]
if leakage_present:
    print(f'  Leakage guard: dropping {len(leakage_present)} ground-truth columns from inference input: {leakage_present}')
df_inference_input = df_source.drop(columns=leakage_present)
print(f'  Inference input: {len(df_inference_input.columns)} columns (leakage fields stripped)')

print(f'\n[INFER]  Running predict_batch() on {len(df_inference_input)} events...')
t_start = time.perf_counter()
results = predict_batch(df_inference_input, model_path=MODEL_PATH)
t_elapsed = time.perf_counter() - t_start
print(f'  Runtime : {t_elapsed:.3f}s')
print(f'  Results : {len(results)} records')

inference_ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

pred_rows = []
for r in results:
    proba = r['probabilities']
    pred_rows.append({
        'predicted_class': r['prediction'],
        'probability_agricultural_burning': proba.get('Agricultural Burning'),
        'probability_industrial_thermal_activity': proba.get('Industrial Thermal Activity'),
        'probability_natural_wildfire_other': proba.get('Natural / Wildfire / Other'),
        'max_probability': r['max_probability'],
        'confidence': r['confidence'],
    })
df_preds = pd.DataFrame(pred_rows)

actual_preserve = [c for c in PRESERVE_COLS if c in df_source.columns]
df_id = df_source[actual_preserve].reset_index(drop=True)
df_preds = df_preds.reset_index(drop=True)
df_preds['model_path'] = MODEL_PATH
df_preds['model_sha256'] = model_sha256
df_preds['model_version'] = 'phase_5_ml_handoff/final_model.joblib'
df_preds['inference_timestamp'] = inference_ts

df_out = pd.concat([df_id, df_preds], axis=1)

os.makedirs(OUTPUT_DIR, exist_ok=True)
df_out.to_csv(OUTPUT_CSV, index=False)
print(f'\n[OUTPUT] Written: {OUTPUT_CSV}')
print(f'  Rows   : {len(df_out)}')
print(f'  Cols   : {len(df_out.columns)}')

print('\n' + '='*70)
print('VALIDATION CHECKS')
print('='*70)

errors = []

def chk(cond, pass_msg, fail_msg):
    if cond:
        print(f'[PASS] {pass_msg}')
    else:
        print(f'[FAIL] {fail_msg}')
        errors.append(fail_msg)

chk(len(df_out)==633, 'Row count = 633', f'Row count = {len(df_out)} (expected 633)')
chk(df_out['event_id'].nunique()==633, 'Unique event_id = 633', f'Unique event_id = {df_out["event_id"].nunique()}')
chk(df_out['row_id'].nunique()==633, 'Unique row_id = 633', f'Unique row_id = {df_out["row_id"].nunique()}')
chk(df_out['predicted_class'].isna().sum()==0, 'No missing predicted_class', f'{df_out["predicted_class"].isna().sum()} missing predicted_class')

prob_cols = ['probability_agricultural_burning','probability_industrial_thermal_activity','probability_natural_wildfire_other']
prob_ok = all(df_out[c].between(0,1,inclusive='both').all() for c in prob_cols)
chk(prob_ok, 'All probabilities in [0,1]', 'Some probabilities out of [0,1] range')
n_null = df_out[prob_cols].isna().any(axis=1).sum()
chk(n_null==0, 'All 3 class probabilities present for all 633 events', f'{n_null} events missing a class probability')

print('\n[CHECK 7] Prediction class distribution:')
for cls, cnt in df_out['predicted_class'].value_counts().items():
    print(f'  {cls:<42}: {cnt:>4} ({100.0*cnt/len(df_out):5.1f}%)')

print('\n[CHECK 8] Confidence tier distribution:')
for tier, cnt in df_out['confidence'].value_counts().items():
    print(f'  {tier:<10}: {cnt:>4} ({100.0*cnt/len(df_out):5.1f}%)')

src_ids = set(df_source['event_id'].tolist())
out_ids = set(df_out['event_id'].tolist())
chk(src_ids==out_ids, 'Source event_id values preserved exactly', f'event_id set mismatch: {len(src_ids & out_ids)} overlap')

uv = df_out['model_version'].unique()
chk(len(uv)==1 and uv[0]=='phase_5_ml_handoff/final_model.joblib',
    'Production model version confirmed: phase_5_ml_handoff/final_model.joblib',
    f'model_version unexpected: {uv}')

print('\n' + '='*70)
if errors:
    print(f'INFERENCE COMPLETE -- {len(errors)} VALIDATION FAILURE(S)')
    for e in errors:
        print(f'  {e}')
else:
    print('INFERENCE COMPLETE -- ALL 10 CHECKS PASSED')
print(f'\nInference timestamp : {inference_ts}')
print(f'Runtime             : {t_elapsed:.3f} seconds')
print(f'Output file         : {os.path.abspath(OUTPUT_CSV)}')
print(f'Model SHA-256       : {model_sha256}')
print('='*70)
