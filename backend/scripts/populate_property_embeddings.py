"""
Populate Properties Table Description Embeddings
Alternative approach: adds embeddings directly to properties table
"""

import asyncio
import sys
from datetime import datetime
from tqdm import tqdm

from backend.config import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from backend.neon_client import select, update, call_rpc
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
    print("🤖 Populating Properties Description Embeddings")
    print("=" * 70 + "\n")
    
    try:
        # Fetch properties without embeddings
        print("📊 Fetching properties without embeddings...")
        properties = await select(
            "properties",
            select_fields="*",
            limit=10000
        )
        
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
        
        # Generate embeddings
        print("🔄 Generating embeddings (OpenAI)...")
        all_embeddings = await embed_batch(descriptions, batch_size=50)
        
        print()
        
        # Update properties with embeddings
        print("💾 Updating properties with embeddings...")
        batch_size = 50
        total_updated = 0
        total_errors = 0
        
        for i in tqdm(range(0, len(property_ids), batch_size), desc="Updating"):
            batch_ids = property_ids[i:i + batch_size]
            batch_embeddings = all_embeddings[i:i + batch_size]
            
            for prop_id, embedding in zip(batch_ids, batch_embeddings):
                try:
                    result = await update(
                        "properties",
                        {"id": prop_id},
                        {
                            "description_embedding": embedding,
                            "embedding_model": EMBEDDING_MODEL,
                            "embedding_generated_at": datetime.utcnow().isoformat()
                        }
                    )
                    total_updated += 1
                except Exception as e:
                    print(f"❌ Error updating property {prop_id}: {e}")
                    total_errors += 1
        
        print()
        print("=" * 70)
        print("✅ Property Embeddings Population Complete!")
        print("=" * 70)
        print(f"📊 Results:")
        print(f"   ✅ Updated: {total_updated}")
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
                coverage = (result.get('properties_with_embeddings', 0) / max(result.get('property_count', 1), 1)) * 100
                print(f"   Coverage: {coverage:.1f}%")
        except Exception as e:
            print(f"⚠️  Could not fetch stats: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
