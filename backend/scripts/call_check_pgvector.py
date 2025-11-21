"""
Call the check_pgvector RPC function to verify pgvector extension status
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def check_pgvector_status():
    """Call the check_pgvector RPC function"""
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        sys.exit(1)
    
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/check_pgvector"
    
    print("\n" + "="*70)
    print("🔍 Checking pgvector Extension Status")
    print("="*70 + "\n")
    
    try:
        response = requests.post(url, headers=headers, json={}, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            print("📊 Results:\n")
            print(f"   Database: {result.get('database')}")
            print(f"   Timestamp: {result.get('timestamp')}")
            print()
            
            # Installation status
            installed = result.get('pgvector_installed', False)
            version = result.get('pgvector_version')
            
            if installed:
                print(f"   ✅ pgvector INSTALLED: v{version}")
            else:
                print(f"   ❌ pgvector NOT INSTALLED")
            print()
            
            # Availability
            available = result.get('pgvector_available', False)
            avail_version = result.get('available_version')
            
            if available:
                print(f"   ✅ pgvector AVAILABLE: v{avail_version}")
            else:
                print(f"   ❌ pgvector NOT AVAILABLE on this server")
            print()
            
            # Vector type
            vector_type = result.get('vector_type_exists', False)
            print(f"   {'✅' if vector_type else '❌'} Vector type exists: {vector_type}")
            print()
            
            # Vector columns
            vector_cols = result.get('vector_columns_count', 0)
            print(f"   📊 Vector columns in database: {vector_cols}")
            print()
            
            # Operators
            operators = result.get('vector_operators', [])
            if operators:
                print(f"   🔧 Vector operators available ({len(operators)}):")
                for op in operators[:5]:
                    print(f"      - {op}")
                if len(operators) > 5:
                    print(f"      ... and {len(operators) - 5} more")
            else:
                print(f"   ⚠️  No vector operators found")
            print()
            
            # Summary
            print("="*70)
            if installed and vector_type:
                print("✅ STATUS: pgvector is FULLY OPERATIONAL")
                print("="*70 + "\n")
                print("🎉 You can use pgvector features:")
                print("   - Store vector embeddings (e.g. property descriptions)")
                print("   - Semantic similarity search")
                print("   - Cosine/L2 distance calculations")
                print("   - Nearest neighbor queries")
                print()
                
                # Example usage
                print("📝 Example Usage:")
                print("   -- Store embeddings:")
                print("   ALTER TABLE properties ADD COLUMN embedding vector(1536);")
                print()
                print("   -- Find similar properties:")
                print("   SELECT * FROM properties")
                print("   ORDER BY embedding <-> '[0.1, 0.2, ...]'::vector")
                print("   LIMIT 10;")
                
            elif available and not installed:
                print("⚠️  STATUS: pgvector AVAILABLE but NOT ENABLED")
                print("="*70 + "\n")
                print("📋 To enable pgvector:")
                print("   1. Go to Supabase Dashboard")
                print("   2. Database → Extensions")
                print("   3. Search 'vector' and click 'Enable'")
                print()
                print("   Or run this SQL:")
                print("   CREATE EXTENSION IF NOT EXISTS vector;")
                
            else:
                print("❌ STATUS: pgvector NOT AVAILABLE")
                print("="*70 + "\n")
                print("⚠️  Your Supabase instance doesn't have pgvector available.")
                print("   Contact Supabase support or upgrade your plan.")
            
            print("\n" + "="*70 + "\n")
            
        elif response.status_code == 404:
            print("❌ Error: check_pgvector RPC function not found")
            print()
            print("📋 Next Steps:")
            print("   1. Open Supabase SQL Editor")
            print("   2. Run the SQL from: database/functions/check_pgvector.sql")
            print("   3. Run this script again")
            print()
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_pgvector_status()
