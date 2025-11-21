import asyncio
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def check():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Try getting records at offset 10000
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/transactions',
            params={'select': 'id,source_file', 'limit': 5, 'offset': 10000},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                'Prefer': 'count=exact'
            }
        )
        print(f'Content-Range: {r.headers.get("content-range")}')
        print(f'Records at offset 10000: {len(r.json())}')
        if r.json():
            print(f'Sample: {r.json()[0]}')

asyncio.run(check())
