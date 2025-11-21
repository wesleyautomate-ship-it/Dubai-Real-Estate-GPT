"""Test search API directly"""
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "http://localhost:8787/api/search",
            params={"q": "Dubai Marina", "limit": 5}
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Total: {result.get('total')}")
        print(f"Results: {len(result.get('results', []))}")
        if result.get('results'):
            print(f"First result: {result['results'][0]}")
        else:
            print(f"Response: {result}")

asyncio.run(test())
