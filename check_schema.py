import asyncio
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def check():
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/transactions',
            params={'select': '*', 'limit': 1},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            }
        )
        data = r.json()
        
        if data:
            print("Transactions table columns:")
            for key in sorted(data[0].keys()):
                value = data[0][key]
                value_str = str(value)[:50] if value else "NULL"
                print(f"  - {key:25} = {value_str}")

asyncio.run(check())
