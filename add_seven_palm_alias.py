"""Add/update Seven Palm alias"""
import asyncio
from backend.supabase_client import upsert, select

async def add_alias():
    # First check if the actual building exists
    print("Checking for 'Seven Palm' variations in buildings...")
    buildings = await select(
        "transactions",
        select_fields="building",
        filters={"building": "ilike.%seven%palm%"},
        limit=20
    )
    
    unique_buildings = set([b['building'] for b in buildings])
    print(f"Found {len(unique_buildings)} buildings:")
    for b in unique_buildings:
        print(f"  - {b}")
    
    if unique_buildings:
        canonical = list(unique_buildings)[0]
        print(f"\nAdding alias: 'Seven Palm' → '{canonical}'")
        
        await upsert(
            "aliases",
            {
                "alias": "Seven Palm",
                "canonical": canonical,
                "type": "building",
                "confidence": 0.9
            }
        )
        print("✓ Alias added!")
    else:
        print("\n✗ No 'Seven Palm' building found in database")

asyncio.run(add_alias())
