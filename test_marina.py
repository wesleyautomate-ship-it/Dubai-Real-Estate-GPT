"""Check if Dubai Marina properties exist"""
import asyncio
from backend.supabase_client import select

async def test_marina():
    # Test: Get properties with Marina in community
    print("Checking for Marina properties...")
    
    result = await select(
        "transactions",
        select_fields="community,building,unit,buyer_name,price",
        filters={"community": "ilike.%MARINA%"},
        limit=10
    )
    
    print(f"Found {len(result)} Marina transactions")
    for r in result[:5]:
        print(f"  {r.get('unit')} at {r.get('building')} - {r.get('community')} - AED {r.get('price', 0):,.0f}")
    
    # Also check properties table
    print("\nChecking properties table...")
    props = await select(
        "properties",
        select_fields="unit,building,community",
        filters={},
        limit=20
    )
    
    print(f"\nSample of {len(props)} properties:")
    for p in props[:5]:
        print(f"  {p.get('unit')} at {p.get('building')} - Community: {p.get('community')}")

if __name__ == "__main__":
    asyncio.run(test_marina())
