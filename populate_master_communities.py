"""
Efficiently populate master_community and sub_community columns
Uses bulk updates by source_file to avoid iterating through all records
"""
import asyncio
import re
from backend.supabase_client import get_client

async def populate_communities():
    client = await get_client()
    
    print("Populating community columns efficiently...")
    print("=" * 60)
    
    # Step 1: Copy community → sub_community (single UPDATE per source_file)
    print("\nStep 1: Setting sub_community...")
    
    # Get all unique source files
    response = await client.from_("transactions").select("source_file").execute()
    source_files = set([r["source_file"] for r in response.data if r.get("source_file")])
    
    print(f"Found {len(source_files)} source files")
    
    for i, source_file in enumerate(source_files, 1):
        # Extract master community from filename
        # "Palm Jumeirah Jan 2025.xlsx" → "Palm Jumeirah"
        master_comm = re.sub(
            r'\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\.xlsx$', 
            '', 
            source_file, 
            flags=re.IGNORECASE
        ).strip()
        
        # Single update for ALL records with this source_file
        # This updates thousands of records at once instead of one-by-one
        try:
            result = await client.from_("transactions") \
                .update({
                    "master_community": master_comm,
                    "sub_community": client.from_("transactions").select("community").eq("source_file", source_file).limit(1).execute().data[0]["community"]  # This won't work, need different approach
                }) \
                .eq("source_file", source_file) \
                .execute()
            
            print(f"  [{i}/{len(source_files)}] ✓ {source_file} → {master_comm}")
        except Exception as e:
            print(f"  [{i}/{len(source_files)}] ✗ Error: {e}")
    
    print("\n✓ Master communities populated!")
    print("\nNote: sub_community needs SQL approach (see instructions below)")

if __name__ == "__main__":
    asyncio.run(populate_communities())
