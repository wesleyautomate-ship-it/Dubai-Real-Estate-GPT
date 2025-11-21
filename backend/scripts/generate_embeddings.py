"""
Generate Embeddings for Property Descriptions
Uses OpenAI ada-002 to create vector embeddings for semantic search
"""

import os
import sys
import json
import time
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Embedding model settings
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIMENSION = 1536
BATCH_SIZE = 500  # Process 500 properties at a time (5x faster!)
RATE_LIMIT_DELAY = 0.1  # Reduced to 0.1 seconds between batches

client = OpenAI(api_key=OPENAI_API_KEY)


def fetch_properties_without_embeddings(limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetch properties that don't have embeddings yet
    """
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    
    url = f"{SUPABASE_URL}/rest/v1/properties"
    params = {
        "select": "id,community,building,unit,type,bedrooms,bathrooms,size_sqft,last_price",
        "description_embedding": "is.null",
        "limit": limit,
        "order": "id"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch properties: {response.status_code} {response.text}")


def generate_property_description(prop: Dict[str, Any]) -> str:
    """
    Generate a natural language description from property data
    """
    parts = []
    
    # Basic info
    if prop.get('bedrooms'):
        parts.append(f"{prop['bedrooms']} bedroom")
    
    if prop.get('type'):
        parts.append(prop['type'].lower())
    
    # Location
    if prop.get('building'):
        parts.append(f"in {prop['building']}")
    
    if prop.get('community'):
        parts.append(f"{prop['community']}")
    
    if prop.get('unit'):
        parts.append(f"unit {prop['unit']}")
    
    # Size
    if prop.get('size_sqft'):
        parts.append(f"with {prop['size_sqft']} sqft")
    
    # Price
    if prop.get('last_price'):
        price_m = prop['last_price'] / 1_000_000
        parts.append(f"priced at AED {price_m:.2f}M")
    
    description = " ".join(parts)
    
    # Fallback if no data
    if not description.strip():
        description = f"Property {prop.get('id', 'unknown')}"
    
    return description


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings using OpenAI API
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        
        return [item.embedding for item in response.data]
    
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        raise


def update_property_embedding(property_id: str, embedding: List[float], max_retries: int = 3) -> bool:
    """
    Update a property with its embedding (with retry logic)
    """
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/properties"
    params = {"id": f"eq.{property_id}"}
    
    payload = {
        "description_embedding": embedding,
        "embedding_generated_at": "now()",
        "embedding_model": EMBEDDING_MODEL
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.patch(url, headers=headers, params=params, json=payload, timeout=30)
            return response.status_code in [200, 204]
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))  # Exponential backoff
    
    return False


def process_batch(properties: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Process a batch of properties
    """
    stats = {"success": 0, "failed": 0}
    
    # Generate descriptions
    descriptions = [generate_property_description(prop) for prop in properties]
    
    # Generate embeddings
    try:
        embeddings = generate_embeddings(descriptions)
        
        # Update database
        for prop, embedding in zip(properties, embeddings):
            try:
                if update_property_embedding(prop['id'], embedding):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                    print(f"  ❌ Failed to update: {prop['id']}")
            except Exception as e:
                stats["failed"] += 1
                print(f"  ❌ Error updating {prop['id']}: {e}")
        
    except Exception as e:
        print(f"  ❌ Batch embedding failed: {e}")
        stats["failed"] = len(properties)
    
    return stats


def main():
    """
    Main execution function - runs in a loop to process ALL properties
    """
    print("\n" + "="*70)
    print("🤖 Property Embedding Generator")
    print("="*70 + "\n")
    
    # Validate configuration
    if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY]):
        print("❌ Error: Missing required environment variables")
        print("   Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY")
        sys.exit(1)
    
    print("📊 Configuration:")
    print(f"   Embedding Model: {EMBEDDING_MODEL}")
    print(f"   Dimensions: {EMBEDDING_DIMENSION}")
    print(f"   Batch Size: {BATCH_SIZE}")
    print()
    
    # Process in continuous loop until no more properties without embeddings
    total_processed = 0
    total_stats = {"success": 0, "failed": 0}
    iteration = 1
    
    while True:
        # Fetch next batch of properties without embeddings
        print(f"🔍 Iteration {iteration}: Fetching properties without embeddings...")
        try:
            properties = fetch_properties_without_embeddings(limit=5000)  # Fetch 5000 at a time (5x faster!)
            batch_count = len(properties)
            
            if batch_count == 0:
                print("\n✅ All properties now have embeddings!")
                break
            
            print(f"   Found {batch_count} properties to process in this iteration")
            print()
        except Exception as e:
            print(f"❌ Error fetching properties: {e}")
            break
        
        # Process properties in batches of BATCH_SIZE
        sub_batch_count = (batch_count + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"⚙️  Processing {sub_batch_count} batches...\n")
        
        for i in range(0, batch_count, BATCH_SIZE):
            batch = properties[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            print(f"📦 Batch {batch_num}/{sub_batch_count} ({len(batch)} properties)")
            
            stats = process_batch(batch)
            total_stats["success"] += stats["success"]
            total_stats["failed"] += stats["failed"]
            total_processed += len(batch)
            
            print(f"   ✅ Success: {stats['success']}, ❌ Failed: {stats['failed']}")
            
            # Rate limiting
            if i + BATCH_SIZE < batch_count:
                print(f"   ⏳ Waiting {RATE_LIMIT_DELAY}s before next batch...")
                time.sleep(RATE_LIMIT_DELAY)
            
            print()
        
        print(f"📊 Iteration {iteration} complete: Processed {batch_count} properties")
        print(f"   Total so far: {total_processed} properties ({total_stats['success']} success, {total_stats['failed']} failed)\n")
        iteration += 1
    
    # Summary
    print("="*70)
    print("✅ Embedding Generation Complete!")
    print("="*70 + "\n")
    print(f"📊 Results:")
    print(f"   Total Processed: {total_processed}")
    print(f"   ✅ Successful: {total_stats['success']}")
    print(f"   ❌ Failed: {total_stats['failed']}")
    if total_processed > 0:
        print(f"   Success Rate: {(total_stats['success'] / total_processed * 100):.1f}%")
    print()
    
    # Cost estimate
    # OpenAI ada-002: ~$0.0001 per 1K tokens
    # Average property description: ~50 tokens
    estimated_cost = (total_processed * 50 / 1000) * 0.0001
    print(f"💰 Estimated Cost: ${estimated_cost:.4f} USD")
    print()
    
    # Check embedding stats via RPC
    print("🔍 Verifying embedding stats...")
    try:
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        url = f"{SUPABASE_URL}/rest/v1/rpc/get_embedding_stats"
        response = requests.post(url, headers=headers, json={}, timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"   Total Properties: {stats.get('total_properties', 'N/A')}")
            print(f"   With Embeddings: {stats.get('with_description_embedding', 'N/A')}")
            print(f"   Coverage: {stats.get('embedding_coverage_pct', 'N/A')}%")
        else:
            print("   ⚠️  Could not fetch stats (RPC function may not exist yet)")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    print()
    print("="*70)
    print("🎉 Ready for semantic search!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
