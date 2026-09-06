import re, pandas as pd

with open("outputs/phase_5b_dashboard/dashboard_schema_design.md", encoding="utf-8") as f:
    schema_md = f.read()

# 1. Check total fields claim
header_m = re.search(r"\*\*Total fields:\s*(\d+)\*\*", schema_md)
claimed_total = int(header_m.group(1)) if header_m else None
print("=== CORRECTED SUMMARY BLOCK ===")
print("Total fields claim:", claimed_total)

# 2. Check group counts in summary code block
block_m = re.search(r"## RECOMMENDED FINAL SCHEMA.*?```(.*?)```", schema_md, re.DOTALL)
block_text = block_m.group(1).strip() if block_m else ""
print()
print(block_text)
group_counts = re.findall(r"\((\d+)\s+fields?\)", block_text)
total_from_groups = sum(int(x) for x in group_counts)
print()
print("Group counts:", group_counts)
print("Sum of group counts:", total_from_groups)
print()

# 3. Extract table fields
table_fields = re.findall(r"\|\s*\d+\s*\|\s*`([^`]+)`", schema_md)
unique_table_fields = list(dict.fromkeys(table_fields))
print("Fields in schema tables:", len(unique_table_fields))
print()

# 4. Compare against CSV
df = pd.read_csv("outputs/phase_5b_dashboard/dashboard_events_633.csv", nrows=0)
csv_cols = set(df.columns)
schema_cols = set(unique_table_fields)

extra_in_csv = sorted(csv_cols - schema_cols)
extra_in_schema = sorted(schema_cols - csv_cols)

print("=== VERIFICATION RESULTS ===")
ok1 = claimed_total == 61
ok2 = total_from_groups == 61
ok3 = len(extra_in_csv) == 0
ok4 = len(extra_in_schema) == 0

print("PASS" if ok1 else "FAIL", "Summary block claims 61 fields (actual:", claimed_total, ")")
print("PASS" if ok2 else "FAIL", "Group counts sum to 61 (actual:", total_from_groups, ")")
print("PASS" if ok3 else "FAIL", "No CSV field missing from schema (missing:", extra_in_csv, ")")
print("PASS" if ok4 else "FAIL", "No schema field absent from CSV (extra:", extra_in_schema, ")")
print()

print("Corrected group breakdown:")
labels = ["A","B","C","D","E","F","G","H","I"]
for label, count in zip(labels, group_counts):
    print(f"  GROUP {label}: {count} fields")
print("  TOTAL:", total_from_groups)
