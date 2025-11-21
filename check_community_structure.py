"""Check current community vs building structure"""
import asyncio
from backend.supabase_client import select

async def check():
    result = await select(
        "transactions",
        select_fields="community,building,source_file",
        filters={},
        limit=10
    )
    
    print("Current data structure:\n")
    print(f"{'Source File':<40} | {'Community':<30} | {'Building'}")
    print("-" * 100)
    
    for r in result:
        print(f"{r['source_file']:<40} | {r['community']:<30} | {r['building']}")

asyncio.run(check())
