import asyncio
from backend.supabase_client import call_rpc

async def get_all_sources():
    # Use SQL aggregation to get unique source files
    result = await call_rpc("query", {
        "query": "SELECT DISTINCT source_file FROM transactions WHERE source_file IS NOT NULL ORDER BY source_file"
    })
    
    if result:
        print(f"Total unique source files in database: {len(result)}\n")
        for i, row in enumerate(result, 1):
            print(f"{i:3d}. {row['source_file']}")
    else:
        print("No source files found")

asyncio.run(get_all_sources())
