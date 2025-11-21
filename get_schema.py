import asyncio
import httpx
import json
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def get_schema():
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/',
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            }
        )
        data = r.json()
        print(json.dumps(data, indent=2))

asyncio.run(get_schema())
