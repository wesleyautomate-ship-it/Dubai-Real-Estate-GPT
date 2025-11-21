"""Bulk insert all Dubai real estate aliases into database"""
import asyncio
from backend.supabase_client import upsert, select
from dubai_aliases import ALL_ALIASES

async def bulk_insert():
    print(f"Preparing to insert {len(ALL_ALIASES)} aliases...")
    
    # Check existing aliases to avoid duplicates
    print("\nChecking existing aliases...")
    existing = await select("aliases", select_fields="alias", filters={}, limit=1000)
    existing_aliases = set([a['alias'] for a in existing])
    print(f"Found {len(existing_aliases)} existing aliases")
    
    # Filter out aliases that already exist
    new_aliases = [a for a in ALL_ALIASES if a['alias'] not in existing_aliases]
    print(f"\n{len(new_aliases)} new aliases to add")
    
    if not new_aliases:
        print("✓ All aliases already exist!")
        return
    
    # Insert in batches
    batch_size = 50
    success_count = 0
    error_count = 0
    
    for i in range(0, len(new_aliases), batch_size):
        batch = new_aliases[i:i+batch_size]
        try:
            await upsert("aliases", batch)
            success_count += len(batch)
            print(f"  ✓ Inserted batch {i//batch_size + 1} ({len(batch)} aliases)")
        except Exception as e:
            error_count += len(batch)
            print(f"  ✗ Error in batch {i//batch_size + 1}: {e}")
    
    print(f"\n{'='*60}")
    print(f"✓ Insertion complete!")
    print(f"  - Successfully added: {success_count}")
    print(f"  - Errors: {error_count}")
    print(f"  - Total aliases in database: {len(existing_aliases) + success_count}")
    
    # Show some examples
    print(f"\n{'='*60}")
    print("Sample aliases added:")
    for alias in new_aliases[:10]:
        print(f"  '{alias['alias']}' → '{alias['canonical']}' ({alias['type']})")

asyncio.run(bulk_insert())
