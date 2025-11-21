"""Check transactions table for unit 905"""
import asyncio
from backend.supabase_client import select

async def check_transactions():
    # Get transactions for unit 905
    print("Getting transactions for unit 905...")
    result = await select(
        "transactions",
        select_fields="*",
        filters={"unit": "905"},
        limit=3
    )
    
    print(f"\nFound {len(result)} transactions for unit 905:")
    for txn in result:
        print(f"\n  Transaction:")
        for key, value in sorted(txn.items()):
            value_str = str(value)[:100] if value else "None"
            print(f"    {key}: {value_str}")

if __name__ == "__main__":
    asyncio.run(check_transactions())
