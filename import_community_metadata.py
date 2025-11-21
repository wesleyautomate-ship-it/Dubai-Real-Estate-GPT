"""Import community metadata from JSON to database"""
import asyncio
import json
from backend.supabase_client import upsert

async def import_metadata():
    # Load JSON file
    print("Loading community metadata from JSON...")
    with open('community_metadata.json', 'r', encoding='utf-8') as f:
        communities = json.load(f)
    
    print(f"Found {len(communities)} communities to import")
    
    # Transform data to match database schema
    records = []
    for comm in communities:
        record = {
            "community": comm["Community"],
            "type": comm.get("Type"),
            "sub_clusters": comm.get("Sub-clusters"),
            "property_types": comm.get("Property types"),
            "bedroom_range": comm.get("Bedroom range"),
            "avg_price_sale": comm.get("Avg Price (Sale)"),
            "avg_rent": comm.get("Avg Rent"),
            "rental_yield": comm.get("Rental yield"),
            "service_charge": comm.get("Service charge"),
            "demographics": comm.get("Demographics"),
            "nearby_infra": comm.get("Nearby infra"),
            "developer": comm.get("Developer")
        }
        records.append(record)
    
    # Import in batches
    print("\nImporting to database...")
    batch_size = 10
    success_count = 0
    error_count = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            await upsert("community_metadata", batch)
            success_count += len(batch)
            print(f"  ✓ Imported batch {i//batch_size + 1} ({len(batch)} communities)")
            
            # Show some examples
            for rec in batch[:2]:
                print(f"    - {rec['community']}: {rec['type']}")
        except Exception as e:
            error_count += len(batch)
            print(f"  ✗ Error in batch {i//batch_size + 1}: {e}")
    
    print(f"\n{'='*60}")
    print(f"✓ Import complete!")
    print(f"  - Successfully imported: {success_count}")
    print(f"  - Errors: {error_count}")
    print(f"\n{'='*60}")
    print("Community metadata features enabled:")
    print("  • Rich community information in search results")
    print("  • Price range filtering")
    print("  • Demographics-based recommendations")
    print("  • Rental yield comparisons")
    print("  • Nearby infrastructure details")

asyncio.run(import_metadata())
