"""
Populate Chunks Table with Property Embeddings
Generates embeddings for property descriptions and inserts into chunks table
"""

import asyncio
import sys
from datetime import datetime
from tqdm import tqdm

from backend.config import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from backend.supabase_client import select, insert, call_rpc
from backend.embeddings import embed_batch


async def generate_property_description(prop: dict) -> str:
    """Generate natural language description from property data"""
    parts = []
    
    if prop.get('bedrooms'):
        parts.append(f"{int(prop['bedrooms'])} bedroom")
    
    if prop.get('type'):
        parts.append(prop['type'].lower())
    
    if prop.get('building'):
        parts.append(f"in {prop['building']}")
    
    if prop.get('community'):
        parts.append(f"{prop['community']}")
    
    if prop.get('unit'):
        parts.append(f"unit {prop['unit']}")
    
    if prop.get('size_sqft'):
        parts.append(f"with {int(prop['size_sqft'])} sqft")
    
    if prop.get('last_price'):
        price_m = prop['last_price'] / 1_000_000
        parts.append(f"priced at AED {price_m:.1f}M")
    
    description = " ".join(parts)
    
    if not description.strip():
        description = f"Property ID {prop.get('id', 'unknown')}"
    
    return description


async def main():
    """Main execution function"""
    print("\n" + "=" * 70)
    print("🤖 Populating Chunks Table with Property Embeddings")
    print("=" * 70 + "\n")
    
    try:
        # Fetch all properties
        print("📊 Fetching properties from Supabase...")
        properties = await select("properties", select_fields="*", limit=10000)
        
        if not properties:
            print("❌ No properties found")
            return
        
        print(f"✅ Found {len(properties)} properties\n")
        
        # Generate descriptions
        print("📝 Generating descriptions...")
        descriptions = []
        property_ids = []
        
        for prop in tqdm(properties, desc="Descriptions"):
            desc = await generate_property_description(prop)
            descriptions.append(desc)
            property_ids.append(prop['id'])
        
        print()
        
        # Generate embeddings in batches
        print("🔄 Generating embeddings (OpenAI)...")
        all_embeddings = await embed_batch(descriptions, batch_size=50)
        
        print()
        
        # Prepare chunks for insertion
        print("📦 Preparing chunks for insertion...")
        chunks = []
        for i, (prop_id, embedding, description) in enumerate(
            tqdm(zip(property_ids, all_embeddings, descriptions), total=len(property_ids), desc="Chunks")
        ):
            chunks.append({
                "property_id": prop_id,
                "content": description,
                "embedding": embedding,
                "chunk_type": "property_description",
                "metadata": {
                    "embedding_model": EMBEDDING_MODEL,
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": "populate_chunks.py"
                }
            })
        
        print()
        
        # Insert chunks
        print("💾 Inserting chunks into database...")
        batch_size = 100
        total_inserted = 0
        total_errors = 0
        
        for i in tqdm(range(0, len(chunks), batch_size), desc="Inserting"):
            batch = chunks[i:i + batch_size]
            try:
                result = await insert("chunks", batch)
                total_inserted += len(batch)
            except Exception as e:
                print(f"❌ Error inserting batch {i//batch_size}: {e}")
                total_errors += len(batch)
        
        print()
        print("=" * 70)
        print("✅ Chunks Population Complete!")
        print("=" * 70)
        print(f"📊 Results:")
        print(f"   ✅ Inserted: {total_inserted}")
        print(f"   ❌ Errors: {total_errors}")
        print(f"   💰 Estimated cost: ${(len(descriptions) * 50 / 1000) * 0.00002:.4f} USD")
        print()
        
        # Show stats
        try:
            stats = await call_rpc("db_stats", {})
            if stats:
                result = stats[0]
                print("📊 Database Stats:")
                print(f"   Total properties: {result.get('property_count', 0)}")
                print(f"   Properties with embeddings: {result.get('properties_with_embeddings', 0)}")
                print(f"   Chunks: {result.get('chunks_count', 0)}")
                print(f"   Chunks with embeddings: {result.get('chunks_with_embeddings', 0)}")
        except Exception as e:
            print(f"⚠️  Could not fetch stats: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
