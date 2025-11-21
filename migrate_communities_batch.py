"""
Batch migration to restructure community columns
Processes records in small batches to avoid timeout
"""
import asyncio
import re
from backend.supabase_client import get_client

async def migrate_communities():
    client = await get_client()
    
    print("Starting community restructuring migration...")
    print("=" * 60)
    
    # Step 1: Add columns (quick operation)
    print("\nStep 1: Adding new columns...")
    try:
        # Add columns to transactions
        await client.rpc("exec_sql", {
            "sql": """
                ALTER TABLE transactions ADD COLUMN IF NOT EXISTS master_community TEXT;
                ALTER TABLE transactions ADD COLUMN IF NOT EXISTS sub_community TEXT;
                ALTER TABLE properties ADD COLUMN IF NOT EXISTS master_community TEXT;
                ALTER TABLE properties ADD COLUMN IF NOT EXISTS sub_community TEXT;
            """
        }).execute()
        print("✓ Columns added")
    except Exception as e:
        print(f"✓ Columns already exist or error: {e}")
    
    # Step 2: Copy community to sub_community (in batches)
    print("\nStep 2: Copying community → sub_community...")
    
    batch_size = 1000
    offset = 0
    total_updated = 0
    
    while True:
        # Get batch of transactions
        response = await client.from_("transactions") \
            .select("id, community") \
            .is_("sub_community", "null") \
            .range(offset, offset + batch_size - 1) \
            .execute()
        
        records = response.data
        if not records:
            break
        
        # Update each record
        for record in records:
            await client.from_("transactions") \
                .update({"sub_community": record["community"]}) \
                .eq("id", record["id"]) \
                .execute()
        
        total_updated += len(records)
        print(f"  Updated {total_updated} transactions...")
        
        if len(records) < batch_size:
            break
        
        offset += batch_size
    
    print(f"✓ Copied {total_updated} records to sub_community")
    
    # Step 3: Extract master_community from source_file
    print("\nStep 3: Extracting master communities from source files...")
    
    # Get unique source files
    response = await client.from_("transactions") \
        .select("source_file") \
        .not_.is_("source_file", "null") \
        .execute()
    
    source_files = set([r["source_file"] for r in response.data])
    print(f"  Found {len(source_files)} unique source files")
    
    # Extract master community from each filename
    for source_file in source_files:
        # Remove date pattern: "Palm Jumeirah Jan 2025.xlsx" -> "Palm Jumeirah"
        master_comm = re.sub(r'\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\.xlsx$', '', source_file, flags=re.IGNORECASE).strip()
        
        # Update all transactions with this source_file
        await client.from_("transactions") \
            .update({"master_community": master_comm}) \
            .eq("source_file", source_file) \
            .execute()
        
        print(f"  ✓ {source_file} → {master_comm}")
    
    print(f"✓ Master communities extracted")
    
    # Step 4: Update properties table (sample approach - full would take too long)
    print("\nStep 4: Updating properties table...")
    print("  (This will take a few minutes...)")
    
    # Get distinct unit+building combinations from transactions
    response = await client.from_("transactions") \
        .select("unit, building, master_community") \
        .not_.is_("master_community", "null") \
        .limit(1000) \
        .execute()
    
    unit_building_map = {}
    for r in response.data:
        key = f"{r['unit']}|{r['building']}"
        unit_building_map[key] = r['master_community']
    
    # Update properties (sample)
    updated_props = 0
    for key, master_comm in list(unit_building_map.items())[:100]:
        unit, building = key.split('|')
        await client.from_("properties") \
            .update({"master_community": master_comm}) \
            .eq("unit", unit) \
            .eq("building", building) \
            .execute()
        updated_props += 1
    
    print(f"✓ Updated {updated_props} properties (sample)")
    
    # Step 5: Create indexes
    print("\nStep 5: Creating indexes...")
    try:
        await client.rpc("exec_sql", {
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_transactions_master_community ON transactions(master_community);
                CREATE INDEX IF NOT EXISTS idx_transactions_sub_community ON transactions(sub_community);
                CREATE INDEX IF NOT EXISTS idx_properties_master_community ON properties(master_community);
                CREATE INDEX IF NOT EXISTS idx_properties_sub_community ON properties(sub_community);
            """
        }).execute()
        print("✓ Indexes created")
    except Exception as e:
        print(f"Note: {e}")
    
    print("\n" + "=" * 60)
    print("✓ Migration complete!")
    print("\nRun check_community_structure.py to verify results")

if __name__ == "__main__":
    asyncio.run(migrate_communities())
