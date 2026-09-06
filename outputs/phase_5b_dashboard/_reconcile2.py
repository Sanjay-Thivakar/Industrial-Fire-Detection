import re

with open("outputs/phase_5b_dashboard/dashboard_schema_design.md", encoding="utf-8") as f:
    schema_md = f.read()

# Split into group sections
# Each section starts with "### GROUP X"
sections = re.split(r"(?=### GROUP [A-I])", schema_md)
group_sections = [s for s in sections if s.strip().startswith("### GROUP")]

print("=== GROUP-BY-GROUP ANALYSIS ===")
print()

grand_claimed = 0
grand_table   = 0
grand_fields  = []

for sec in group_sections:
    # Get group header
    header_m = re.match(r"### (GROUP [A-I][^\n]*)", sec)
    header = header_m.group(1).strip() if header_m else "UNKNOWN"

    # Extract claimed count from header e.g. "(6 fields)"
    count_m = re.search(r"\((\d+)\s+fields?\)", header)
    claimed = int(count_m.group(1)) if count_m else None

    # Extract field names from table rows: | # | `fieldname` | ...
    fields = re.findall(r"\|\s*\d+\s*\|\s*`([^`]+)`", sec)

    print(f"{header}")
    print(f"  Claimed in header : {claimed}")
    print(f"  Fields in table   : {len(fields)}")
    for i, f in enumerate(fields):
        print(f"    {i+1:2}. {f}")
    if claimed is not None and claimed != len(fields):
        print(f"  *** DISCREPANCY: header says {claimed}, table has {len(fields)} ***")
    print()

    grand_claimed += (claimed or 0)
    grand_table   += len(fields)
    grand_fields.extend(fields)

print(f"=== TOTALS ===")
print(f"Sum of all group header claims : {grand_claimed}")
print(f"Sum of all group table fields  : {grand_table}")
print(f"Total fields listed in tables  : {len(grand_fields)}")
print(f"Unique fields listed in tables : {len(set(grand_fields))}")
print()

# The "RECOMMENDED FINAL SCHEMA" header block also claims 57 total
intro_57 = re.findall(r"Total fields:\s*(\d+)", schema_md)
summary_block = re.search(r"RECOMMENDED FINAL SCHEMA.*?(?=---)", schema_md, re.DOTALL)
if summary_block:
    block = summary_block.group(0)
    total_claim = re.findall(r"\*\*Total fields:\s*(\d+)\*\*", block)
    group_lines = re.findall(r"GROUP [A-I].*?\((\d+) fields?\)", block)
    print("Summary block group claims:", group_lines)
    print("Summary block total claim:", total_claim)
    sub = sum(int(x) for x in group_lines)
    print("Sum of summary block groups:", sub)
