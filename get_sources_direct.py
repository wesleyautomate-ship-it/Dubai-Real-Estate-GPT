import asyncio
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

async def get_sources():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/transactions",
            params={"select": "source_file"},
            headers={
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        
        # Get unique files
        files = sorted(set([r["source_file"] for r in data if r.get("source_file")]))
        
        print(f"Total unique source files: {len(files)}\n")
        for i, f in enumerate(files, 1):
            print(f"{i:3d}. {f}")

asyncio.run(get_sources())
