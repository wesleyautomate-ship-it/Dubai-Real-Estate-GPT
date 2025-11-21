"""Check if Seven Palm exists"""
import asyncio
from backend.supabase_client import select

async def check():
    # Check as building
    print("Checking as building...")
    result = await select(
        "transactions",
        select_fields="unit,building,community",
        filters={"building": "ilike.%Seven Palm%", "unit": "905"},
        limit=5
    )
    print(f"Found {len(result)} results")
    for r in result[:3]:
        print(f"  Unit: {r['unit']}, Building: {r['building']}, Community: {r['community']}")
    
    # Check as community
    print("\nChecking as community...")
    result2 = await select(
        "transactions",
        select_fields="unit,building,community",
        filters={"community": "ilike.%Seven Palm%", "unit": "905"},
        limit=5
    )
    print(f"Found {len(result2)} results")
    for r in result2[:3]:
        print(f"  Unit: {r['unit']}, Building: {r['building']}, Community: {r['community']}")

asyncio.run(check())
