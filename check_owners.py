import asyncio
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def check():
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/transactions',
            params={'select': 'owner_name', 'limit': 50},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            }
        )
        data = r.json()
        
        print(f"Type: {type(data)}")
        print(f"Sample: {data[:3] if isinstance(data, list) else data}")
        
        if isinstance(data, list):
            print("\nSample owner names:")
            for i, row in enumerate(data[:20], 1):
                if isinstance(row, dict):
                    print(f"{i:2d}. {row.get('owner_name', 'N/A')}")
                else:
                    print(f"{i:2d}. {row}")

asyncio.run(check())
