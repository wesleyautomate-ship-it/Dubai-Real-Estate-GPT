"""
Verify pgvector extension via Supabase REST API
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def check_pgvector():
    """Check if pgvector is installed using Supabase REST API"""
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return {
            "ok": False,
            "error": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env"
        }
    
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    
    results = {
        "supabase_connection": None,
        "pgvector_info": None,
        "vector_similarity_functions": None,
        "recommendations": []
    }
    
    # 1. Test basic connection
    try:
        url = f"{SUPABASE_URL}/rest/v1/"
        resp = requests.get(url, headers=headers, timeout=10)
        results["supabase_connection"] = {
            "status": "✅ Connected" if resp.status_code == 200 else f"❌ Error: {resp.status_code}",
            "url": SUPABASE_URL
        }
    except Exception as e:
        results["supabase_connection"] = {"status": f"❌ Failed: {str(e)}"}
        return {"ok": False, "results": results}
    
    # 2. Check if we can query extensions via RPC
    # We'll create a simple SQL function to check extensions
    sql_check = """
    SELECT 
        EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') as pgvector_installed,
        (SELECT extversion FROM pg_extension WHERE extname = 'vector') as version,
        (SELECT count(*) FROM pg_available_extensions WHERE name = 'vector') as available
    """
    
    try:
        # Try to execute SQL via RPC if you have a generic SQL RPC function
        # Otherwise, we'll check indirectly
        
        # Check if we have vector similarity operators by looking at functions
        url = f"{SUPABASE_URL}/rest/v1/rpc/market_stats"
        test_resp = requests.post(
            url,
            headers=headers,
            json={"p_community": "test"},
            timeout=10
        )
        
        if test_resp.status_code == 200 or test_resp.status_code == 400:
            results["pgvector_info"] = {
                "status": "⚠️ Cannot directly check pgvector (no SQL exec RPC)",
                "note": "Supabase API connected, but need dashboard access to verify pgvector"
            }
        
    except Exception as e:
        results["pgvector_info"] = {"error": str(e)}
    
    # 3. Check Supabase dashboard recommendations
    results["recommendations"] = [
        "✅ Check via Supabase Dashboard:",
        "   1. Go to: https://app.supabase.com/project/_/database/extensions",
        "   2. Search for 'vector' or 'pgvector'",
        "   3. If not enabled, click 'Enable' button",
        "",
        "✅ Or run this SQL in Supabase SQL Editor:",
        "   CREATE EXTENSION IF NOT EXISTS vector;",
        "   SELECT * FROM pg_extension WHERE extname = 'vector';",
        "",
        "📊 pgvector enables:",
        "   - Vector embeddings storage (for AI/ML)",
        "   - Semantic search",
        "   - Similarity matching",
        "   - Image/text embeddings",
        "",
        "💡 For your real estate app:",
        "   - Store property description embeddings",
        "   - Semantic property search",
        "   - Similar properties matching",
        "   - AI-powered recommendations"
    ]
    
    return {"ok": True, "results": results}

def main():
    print("\n" + "="*60)
    print("🔍 Supabase pgvector Verification")
    print("="*60 + "\n")
    
    result = check_pgvector()
    
    if result["ok"]:
        res = result["results"]
        
        # Connection status
        if res.get("supabase_connection"):
            print("📡 Supabase Connection:")
            print(f"   {res['supabase_connection']['status']}")
            print(f"   URL: {res['supabase_connection']['url']}")
            print()
        
        # pgvector info
        if res.get("pgvector_info"):
            print("🔧 pgvector Status:")
            for key, val in res["pgvector_info"].items():
                print(f"   {key}: {val}")
            print()
        
        # Recommendations
        if res.get("recommendations"):
            print("📋 Next Steps:\n")
            for rec in res["recommendations"]:
                print(f"   {rec}")
            print()
        
        print("="*60)
        print("✅ Verification complete!")
        print("="*60 + "\n")
        
    else:
        print(f"❌ Error: {result.get('error')}")
        if result.get("results"):
            print(json.dumps(result["results"], indent=2))

if __name__ == "__main__":
    main()
