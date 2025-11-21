import pandas as pd
import glob
import os

files = glob.glob('.data_raw/*.xlsx')
total_rows = 0
file_stats = []

print("=" * 70)
print("COUNTING ROWS IN EXCEL FILES")
print("=" * 70)

for filepath in sorted(files):
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
        rows = len(df)
        total_rows += rows
        filename = os.path.basename(filepath)
        file_stats.append((filename, rows))
        print(f"{filename:45s} {rows:>10,} rows")
    except Exception as e:
        filename = os.path.basename(filepath)
        print(f"{filename:45s} ERROR: {e}")

print("=" * 70)
print(f"{'TOTAL ROWS ACROSS ALL FILES:':45s} {total_rows:>10,}")
print(f"{'NUMBER OF FILES:':45s} {len(files):>10}")
print("=" * 70)

# Show transaction vs row count discrepancy
print(f"\nDatabase has: 477,220 transactions")
print(f"Excel files have: {total_rows:,} total rows")
print(f"Discrepancy: {total_rows - 477220:,} rows")
print(f"\nNote: Each transaction has 2+ rows (buyer + seller)")
print(f"Expected transactions: ~{total_rows // 2:,}")
