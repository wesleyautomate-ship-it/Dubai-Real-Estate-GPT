import asyncio
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def get_table_count(table_name):
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/{table_name}',
            params={'select': 'count'},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                'Prefer': 'count=exact'
            }
        )
        if r.status_code == 200:
            return r.json()
        else:
            # The Supabase API returns a 200 with the count in the body, but older versions returned it in the header.
            # This is a fallback for older versions.
            content_range = r.headers.get('content-range')
            if content_range:
                return content_range.split('/')[-1]
    return 0

async def main():
    tables = ['transactions', 'properties', 'owners', 'communities', 'buildings']
    counts = await asyncio.gather(*[get_table_count(table) for table in tables])
    
    print("Database Statistics:")
    for table, count in zip(tables, counts):
        # The count can be a dictionary {'count': N} or a string 'N'
        if isinstance(count, dict):
            c = count.get('count', 0)
        else:
            c = count
        print(f"- {table.capitalize()}: {c} rows")

if __name__ == "__main__":
    asyncio.run(main())
