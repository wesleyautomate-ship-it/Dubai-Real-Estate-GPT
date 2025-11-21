"""Check Serenia building details"""
import asyncio
from backend.supabase_client import select

async def check():
    result = await select(
        "transactions",
        select_fields="building,community",
        filters={"building": "ilike.%serenia%"},
        limit=10
    )
    
    print("Serenia buildings and their communities:")
    for r in result:
        print(f"  Building: {r['building']:50} Community: {r['community']}")

asyncio.run(check())
