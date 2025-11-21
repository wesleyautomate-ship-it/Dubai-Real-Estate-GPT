"""Test script to debug unit 905 lookup"""
import asyncio
from backend.supabase_client import select

async def test_unit_lookup():
    # Test 1: Direct unit search
    print("Test 1: Looking for unit 905 (exact match)...")
    result = await select(
        "properties",
        select_fields="unit,community,building,owner_id,last_price",
        filters={"unit": "905"},
        limit=10
    )
    print(f"Found {len(result)} properties with unit=905")
    for p in result[:3]:
        print(f"  - Unit {p.get('unit')}, Community: {p.get('community')}, Building: {p.get('building')}")
    
    # Test 2: What unit values exist?
    print("\nTest 2: Checking unit values that contain '905'...")
    result2 = await select(
        "properties",
        select_fields="unit,community,building",
        filters={"unit": "like.%905%"},
        limit=10
    )
    print(f"Found {len(result2)} properties with unit LIKE %905%")
    for p in result2[:5]:
        print(f"  - Unit '{p.get('unit')}', Community: {p.get('community')}, Building: {p.get('building')}")
    
    # Test 3: Check first 10 units to see format
    print("\nTest 3: Sample of first 10 units to understand format...")
    result3 = await select(
        "properties",
        select_fields="unit,community,building",
        filters={},
        limit=10
    )
    for p in result3:
        print(f"  - Unit '{p.get('unit')}' (type: {type(p.get('unit'))})")

if __name__ == "__main__":
    asyncio.run(test_unit_lookup())
