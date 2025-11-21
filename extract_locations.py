"""Extract all unique communities and buildings from database"""
import asyncio
from backend.supabase_client import select
import json

async def extract():
    print("Extracting communities...")
    communities = await select(
        "transactions",
        select_fields="community",
        filters={},
        limit=1000
    )
    
    unique_communities = sorted(set([c['community'] for c in communities if c['community'] and c['community'] != '0']))
    
    print(f"\nFound {len(unique_communities)} unique communities")
    print("\nTop 50 communities:")
    for c in unique_communities[:50]:
        print(f"  - {c}")
    
    # Save to file
    with open('communities_list.json', 'w') as f:
        json.dump(unique_communities, f, indent=2)
    
    print("\n✓ Saved to communities_list.json")
    
    # Extract buildings
    print("\nExtracting buildings...")
    buildings = await select(
        "transactions",
        select_fields="building",
        filters={},
        limit=1000
    )
    
    unique_buildings = sorted(set([b['building'] for b in buildings if b['building']]))
    print(f"\nFound {len(unique_buildings)} unique buildings")
    print("\nSample buildings:")
    for b in unique_buildings[:30]:
        print(f"  - {b}")
    
    with open('buildings_list.json', 'w') as f:
        json.dump(unique_buildings, f, indent=2)
    
    print("\n✓ Saved to buildings_list.json")

asyncio.run(extract())
