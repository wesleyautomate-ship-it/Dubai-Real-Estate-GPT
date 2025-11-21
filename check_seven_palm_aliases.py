"""Check for Seven Palm in aliases and transactions"""
import asyncio
from backend.supabase_client import select

async def check():
    # Check aliases
    print("Checking aliases for 'Seven Palm'...")
    aliases = await select(
        "aliases",
        select_fields="*",
        filters={"alias": "ilike.%Seven Palm%"},
        limit=10
    )
    print(f"Found {len(aliases)} aliases")
    for a in aliases:
        print(f"  Alias: '{a['alias']}' → Canonical: '{a['canonical']}' (Type: {a['type']})")
    
    # Check actual building names with "Seven"
    print("\nChecking transactions for buildings with 'Seven'...")
    txns = await select(
        "transactions",
        select_fields="building,community",
        filters={"building": "ilike.%Seven%"},
        limit=10
    )
    print(f"Found {len(txns)} buildings")
    seen = set()
    for t in txns:
        key = (t['building'], t['community'])
        if key not in seen:
            seen.add(key)
            print(f"  Building: '{t['building']}' in {t['community']}")

asyncio.run(check())
