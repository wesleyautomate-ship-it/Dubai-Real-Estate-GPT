"""
Simple script to fix community structure
Updates by source_file (bulk updates thousands at once)
"""
import asyncio
import re
from backend.supabase_client import select, update

async def fix_communities():
    print("Fixing community structure...")
    print("This will take a few minutes for 173k records\n")
    
    # Get unique source files (there are only ~20-30 files)
    print("Step 1: Getting source files...")
    response = await select("transactions", select_fields="source_file")
    source_files = list(set([r["source_file"] for r in response if r.get("source_file")]))
    
    print(f"Found {len(source_files)} source files\n")
    
    # For each source file, bulk update ALL its records at once
    print("Step 2: Updating records by source file...")
    failed = []
    
    for i, source_file in enumerate(source_files, 1):
        # Extract master community: "Palm Jumeirah Jan 2025.xlsx" → "Palm Jumeirah"
        master_comm = re.sub(
            r'\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\.xlsx$',
            '',
            source_file,
            flags=re.IGNORECASE
        ).strip()
        
        try:
            # Bulk update ALL records with this source_file
            # This is fast because it's one UPDATE affecting thousands of rows
            await update(
                "transactions",
                filters={"source_file": source_file},
                data={"master_community": master_comm}
            )
            print(f"  [{i:2d}/{len(source_files)}] ✓ {source_file:45} → {master_comm}")
        except Exception as e:
            print(f"  [{i:2d}/{len(source_files)}] ✗ {source_file:45} (ERROR: {str(e)[:40]})")
            failed.append((source_file, master_comm))
    
    print("\n" + "=" * 70)
    if failed:
        print(f"\n⚠ {len(failed)} file(s) failed (likely too large):")
        for sf, mc in failed:
            print(f"  - {sf} → {mc}")
        print("\nThese will need manual SQL updates in Supabase.")
    else:
        print("✓ All files processed successfully!")
    
    print(f"\n✓ Master communities populated for {len(source_files) - len(failed)}/{len(source_files)} files")
    print("\nNext step: Copy community → sub_community")
    print("Run this SQL in Supabase (it's fast):")
    print("\n  UPDATE transactions SET sub_community = community WHERE sub_community IS NULL;")

if __name__ == "__main__":
    asyncio.run(fix_communities())
