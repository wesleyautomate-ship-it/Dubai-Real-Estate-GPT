"""Test Castleton ownership lookup"""
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test parsing
        print("Test 1: Parse 'Who owns 905 at Castleton?'...")
        response = await client.post(
            "http://localhost:8787/api/tools/parse_query",
            json={"query": "Who owns 905 at Castleton?"}
        )
        parsed = response.json()
        print(f"  Parsed entities: {parsed.get('entities')}")
        
        # Test owner lookup with parsed entities
        print("\nTest 2: Owner lookup with parsed entities...")
        entities = parsed.get('entities', {})
        response = await client.post(
            "http://localhost:8787/api/tools/current_owner",
            json=entities
        )
        result = response.json()
        print(f"  Found: {result.get('found')}")
        if result.get('found'):
            print(f"  Owner: {result.get('owner_name')}")
            print(f"  Phone: {result.get('owner_phone')}")
            print(f"  Building: {result.get('building')}")
            print(f"  Community: {result.get('community')}")
        else:
            print(f"  Message: {result.get('message')}")

asyncio.run(test())
