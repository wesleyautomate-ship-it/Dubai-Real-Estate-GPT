"""
Test Queries for Semantic Search API
Validates API endpoints with sample queries
"""

import asyncio
import sys
from datetime import datetime

from backend.supabase_client import call_rpc
from backend.embeddings import embed_text


# Sample test queries
TEST_QUERIES = [
    "3 bedroom apartment in Dubai Marina",
    "Luxury penthouse with sea view",
    "Affordable studio near metro",
    "Two-bed apartment in City Walk under 3M AED"
]


async def test_search(query: str, verbose: bool = True):
    """Test semantic search endpoint"""
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"🔍 Testing: {query}")
        print(f"{'='*70}")
    
    try:
        # Generate embedding
        if verbose:
            print("  1️⃣  Generating embedding...")
        embedding = await embed_text(query)
        if verbose:
            print(f"     ✅ Embedding generated ({len(embedding)} dimensions)")
        
        # Call search RPC
        if verbose:
            print("  2️⃣  Calling semantic_search_chunks RPC...")
        
        results = await call_rpc("semantic_search_chunks", {
            "query_embedding": embedding,
            "match_threshold": 0.70,
            "match_count": 5
        })
        
        if verbose:
            print(f"     ✅ Found {len(results)} results")
        
        # Display top 3
        if verbose and results:
            print("\n  📋 Top Results:")
            for i, result in enumerate(results[:3], 1):
                score = result.get('score', 0)
                community = result.get('community', 'N/A')
                building = result.get('building', 'N/A')
                unit = result.get('unit', 'N/A')
                price = result.get('price_aed', 'N/A')
                
                print(f"\n     #{i} - Match: {score:.1%}")
                print(f"        Location: {building}, {community} Unit {unit}")
                print(f"        Price: AED {price:,}" if isinstance(price, (int, float)) else f"        Price: {price}")
        
        return len(results)
    
    except Exception as e:
        print(f"     ❌ Error: {e}", file=sys.stderr)
        return 0


async def test_stats():
    """Test stats endpoint"""
    print(f"\n{'='*70}")
    print("📊 Testing: /api/stats")
    print(f"{'='*70}")
    
    try:
        print("  Calling db_stats RPC...")
        stats = await call_rpc("db_stats", {})
        
        if stats:
            result = stats[0] if isinstance(stats, list) else stats
            
            print("  ✅ Stats retrieved:")
            print(f"     Total properties: {result.get('property_count', 0):,}")
            print(f"     Average price/sqft: AED {result.get('avg_price_per_sqft', 0):.2f}")
            print(f"     Total chunks: {result.get('chunks_count', 0):,}")
            print(f"     Properties with embeddings: {result.get('properties_with_embeddings', 0):,}")
            print(f"     Chunks with embeddings: {result.get('chunks_with_embeddings', 0):,}")
            print(f"     Last update: {result.get('last_update', 'N/A')}")
            
            return True
        else:
            print("  ❌ No stats returned")
            return False
    
    except Exception as e:
        print(f"  ❌ Error: {e}", file=sys.stderr)
        return False


async def main():
    """Main test runner"""
    print("\n" + "=" * 70)
    print("🧪 Dubai Real Estate Search API - Test Suite")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test stats first
    print("Phase 1: Database Statistics")
    stats_ok = await test_stats()
    
    if not stats_ok:
        print("\n⚠️  Stats test failed. Check database connection.")
        return
    
    # Test search queries
    print("\n" + "=" * 70)
    print("Phase 2: Semantic Search Tests")
    print("=" * 70)
    
    results_summary = []
    
    for query in TEST_QUERIES:
        count = await test_search(query, verbose=True)
        results_summary.append({
            "query": query,
            "results": count
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 Test Summary")
    print("=" * 70)
    
    for item in results_summary:
        status = "✅" if item["results"] > 0 else "⚠️"
        print(f"{status} '{item['query']}': {item['results']} results")
    
    total_results = sum(item["results"] for item in results_summary)
    avg_results = total_results / len(results_summary) if results_summary else 0
    
    print(f"\nTotal results: {total_results}")
    print(f"Average results per query: {avg_results:.1f}")
    
    if all(item["results"] > 0 for item in results_summary):
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️  Some queries returned no results. Check:")
        print("   1. Embeddings are populated (run populate_chunks.py)")
        print("   2. IVFFLAT index exists on embeddings")
        print("   3. Similarity threshold is appropriate")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


if __name__ == "__main__":
    asyncio.run(main())
