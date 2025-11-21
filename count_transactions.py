import asyncio
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def count():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'{SUPABASE_URL}/rest/v1/transactions',
            params={'select': 'id'},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                'Prefer': 'count=exact'
            }
        )
        content_range = response.headers.get('content-range', 'unknown')
        print(f'Total transactions: {content_range}')

asyncio.run(count())
