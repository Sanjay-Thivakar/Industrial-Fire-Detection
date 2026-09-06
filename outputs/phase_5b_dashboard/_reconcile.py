import pandas as pd, ast, re

# Load actual CSV columns
df = pd.read_csv('outputs/phase_5b_dashboard/dashboard_events_633.csv', nrows=0)
actual_61 = list(df.columns)

# Load build script DASHBOARD_COLS
with open('outputs/phase_5b_dashboard/_build_dashboard.py', encoding='utf-8') as f:
    src = f.read()
m = re.search(r'DASHBOARD_COLS\s*=\s*(\[.*?\])', src, re.DOTALL)
build_cols = ast.literal_eval(m.group(1))

# Load schema design markdown
with open('outputs/phase_5b_dashboard/dashboard_schema_design.md', encoding='utf-8') as f:
    schema_md = f.read()

# Extract field names from the data dictionary tables
# Table rows look like: | 1 | `event_id` | ...
table_fields = re.findall(r'\|\s*\d+\s*\|\s*`([^`]+)`', schema_md)
print('=== Fields extracted from schema_design.md tables ===')
for i, fld in enumerate(table_fields):
    print(f'{i+1:3}. {fld}')
print('Total from markdown:', len(table_fields))
print()

# Extract group field count from group headers like "GROUP A — EVENT IDENTITY (6 fields)"
group_counts = re.findall(r'GROUP\s+[A-I]\s*[^\n]*\((\d+)\s+fields?\)', schema_md)
print('Group field counts from headers:', group_counts)
total_from_groups = sum(int(x) for x in group_counts)
print('Sum from group headers:', total_from_groups)
print()

# Set comparisons
actual_set    = set(actual_61)
build_set     = set(build_cols)
schema_md_set = set(table_fields)

print('=== BUILD SCRIPT vs ACTUAL CSV ===')
print('Build cols count:', len(build_cols))
print('Actual CSV cols count:', len(actual_61))
print('In build but not actual:', sorted(build_set - actual_set))
print('In actual but not build:', sorted(actual_set - build_set))
print('Build list == actual list:', actual_61 == build_cols)
print()

print('=== SCHEMA MD TABLE FIELDS vs BUILD SCRIPT ===')
print('Schema MD table fields count:', len(schema_md_set))
print('Schema MD fields NOT in build/actual:', sorted(schema_md_set - build_set))
print('Build fields NOT in schema MD:', sorted(build_set - schema_md_set))
print()

# Find which 4 fields are in the actual CSV but not in the 57-field design
# We need the ground truth 57-field list from the schema design
# The schema design text lists groups A(6)+B(2)+C(15)+D(6)+E(12)+F(2)+G(10)+H(4)+I(5)=62? Let us recount
group_labels = ['A','B','C','D','E','F','G','H','I']
print('=== GROUP LABELS AND CLAIMED COUNTS ===')
for label in group_labels:
    pat = rf'GROUP\s+{label}\b[^\n]*\((\d+)\s+fields?\)'
    hits = re.findall(pat, schema_md)
    print(f'  GROUP {label}: claimed counts found = {hits}')
print()

# The Provenance group in the schema text says "5 fields" but only lists 4 explicit fields
# in the table (inference_timestamp, model_version, model_sha256, data_source_version)
# But the schema also mentions "model_path" as excluded.
# Let us list exactly what the schema md tables contain for group I
print('=== GROUP I (Provenance) table fields from md ===')
# Find the GROUP I section
sec = re.search(r'GROUP I.*?(?=GROUP [A-Z]|##\s*SOURCE|$)', schema_md, re.DOTALL)
if sec:
    grp_i = sec.group(0)
    fields_i = re.findall(r'\|\s*\d+\s*\|\s*`([^`]+)`', grp_i)
    print('  Fields in GROUP I table:', fields_i)
    print('  Count:', len(fields_i))
print()

# Summarise exact difference: the schema design said 57 but the build produced 61
# Let us count all unique table-extracted fields from the schema md
unique_md_fields = list(dict.fromkeys(table_fields))  # preserve order, dedup
print('=== UNIQUE FIELDS FROM SCHEMA MD TABLES (in order, deduped) ===')
for i, fld in enumerate(unique_md_fields):
    print(f'{i+1:3}. {fld}')
print('Total unique:', len(unique_md_fields))
print()

# Final comparison: schema_md_set vs actual_61
extra_in_actual   = sorted(actual_set - schema_md_set)
missing_from_actual = sorted(schema_md_set - actual_set)
print('=== FINAL COMPARISON: actual CSV vs schema_design.md tables ===')
print('Extra in actual CSV (not in schema md tables):', extra_in_actual)
print('Missing from actual CSV (in schema md but not CSV):', missing_from_actual)
print()

# Load actual data to characterise extra fields
df_full = pd.read_csv('outputs/phase_5b_dashboard/dashboard_events_633.csv')
if extra_in_actual:
    print('=== CHARACTERISING EXTRA FIELDS ===')
    for fld in extra_in_actual:
        if fld in df_full.columns:
            s = df_full[fld]
            print(f'  {fld}:')
            print(f'    dtype   : {s.dtype}')
            print(f'    null%   : {100*s.isna().sum()/len(df_full):.1f}%')
            print(f'    unique  : {s.nunique()}')
            print(f'    samples : {list(s.dropna().head(2))}')
        else:
            print(f'  {fld}: NOT IN CSV')
