"""
Complete script to fix community structure for ALL 480k+ records
Properly paginates to get all source files, then bulk updates
"""
import asyncio
import re
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def get_all_source_files():
    """Get all unique source files by paginating through the entire table"""
    print("Fetching all source files from database...")
    
    source_files_set = set()
    offset = 0
    limit = 10000
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                response = await client.get(
                    f'{SUPABASE_URL}/rest/v1/transactions',
                    params={
                        'select': 'source_file',
                        'limit': limit,
                        'offset': offset
                    },
                    headers={
                        'apikey': SUPABASE_SERVICE_ROLE_KEY,
                        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                
                # Add to set
                for row in data:
                    if row.get('source_file'):
                        source_files_set.add(row['source_file'])
                
                print(f"  Processed {offset + len(data):,} records, found {len(source_files_set)} unique files so far...")
                
                # Advance by actual batch size; do not stop early if server caps page size
                offset += len(data)
                
            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code == 500:
                    print(f"  ⚠ Server error at offset {offset:,}. Stopping pagination early.")
                    break
                raise
    
    return sorted(list(source_files_set))

async def update_by_source_file(source_file: str, master_community: str):
    """Bulk update all records with a specific source_file"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.patch(
            f'{SUPABASE_URL}/rest/v1/transactions',
            params={'source_file': f'eq.{source_file}'},
            json={'master_community': master_community},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                'Prefer': 'return=minimal'  # Don't return data, just update
            }
        )
        response.raise_for_status()

async def fix_communities():
    print("=" * 70)
    print("COMMUNITY RESTRUCTURE - Complete Database Update")
    print("=" * 70)
    print()
    
    # Step 1: Get all source files
    source_files = await get_all_source_files()
    print(f"\n✓ Found {len(source_files)} unique source files\n")
    
    # Step 2: Update each source file
    print("Updating master_community for each source file...")
    print("-" * 70)
    
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
            await update_by_source_file(source_file, master_comm)
            print(f"  [{i:3d}/{len(source_files)}] ✓ {source_file:50} → {master_comm}")
        except Exception as e:
            error_msg = str(e)[:60]
            print(f"  [{i:3d}/{len(source_files)}] ✗ {source_file:50} (ERROR: {error_msg})")
            failed.append((source_file, master_comm, error_msg))
    
    # Step 3: Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if failed:
        print(f"\n⚠ {len(failed)} file(s) failed:")
        for sf, mc, err in failed:
            print(f"  - {sf} → {mc}")
            print(f"    Error: {err}")
    else:
        print("\n✓ All files processed successfully!")
    
    success_count = len(source_files) - len(failed)
    print(f"\n✓ Master communities populated for {success_count}/{len(source_files)} files")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("\n1. Copy community → sub_community")
    print("   Run in Supabase SQL editor:")
    print("\n   UPDATE transactions SET sub_community = community WHERE sub_community IS NULL;")
    print("\n2. Verify the changes")
    print("   SELECT master_community, sub_community, building, COUNT(*)")
    print("   FROM transactions")
    print("   GROUP BY master_community, sub_community, building")
    print("   ORDER BY master_community, sub_community;")
    print()

if __name__ == "__main__":
    asyncio.run(fix_communities())
