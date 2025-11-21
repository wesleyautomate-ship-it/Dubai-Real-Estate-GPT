"""Test semantic search to debug why Dubai Marina returns no results"""
import asyncio
from backend.supabase_client import call_rpc

async def test_search():
    # Test 1: Search for "Dubai Marina"
    print("Test 1: Searching for 'Dubai Marina'...")
    try:
        results = await call_rpc(
            "semantic_search_chunks",
            {
                "query_text": "Dubai Marina",
                "match_count": 10
            }
        )
        print(f"Found {len(results)} results")
        for r in results[:3]:
            print(f"  - {r.get('content', 'N/A')[:100]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Check if Dubai Marina properties exist
    print("\nTest 2: Checking if Dubai Marina exists in database...")
    from backend.supabase_client import select
    
    result = await select(
        "transactions",
        select_fields="community,building,count",
        filters={"community": "ilike.%Marina%"},
        limit=10
    )
    print(f"Found {len(result)} transactions with 'Marina' in community")
    for r in result[:5]:
        print(f"  - Community: {r.get('community')}, Building: {r.get('building')}")

if __name__ == "__main__":
    asyncio.run(test_search())
