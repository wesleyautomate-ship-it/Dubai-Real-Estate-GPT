"""Test ownership lookup for 905 at Seven Palm"""
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test parsing
        print("Test 1: Parse query...")
        response = await client.post(
            "http://localhost:8787/api/tools/parse_query",
            json={"query": "Who owns 905 at Seven Palm?"}
        )
        parsed = response.json()
        print(f"  Intent: {parsed.get('intent')}")
        print(f"  Entities: {parsed.get('entities')}")
        
        # Test owner lookup
        print("\nTest 2: Owner lookup...")
        response = await client.post(
            "http://localhost:8787/api/tools/current_owner",
            json={
                "unit": "905",
                "building": "Seven Palm",
                "community": None
            }
        )
        result = response.json()
        print(f"  Found: {result.get('found')}")
        print(f"  Ambiguous: {result.get('ambiguous', False)}")
        if result.get('found'):
            print(f"  Owner: {result.get('owner_name')}")
            print(f"  Building: {result.get('building')}")
            print(f"  Community: {result.get('community')}")
        elif result.get('suggestions'):
            print(f"  Suggestions: {len(result['suggestions'])}")
            for s in result['suggestions'][:2]:
                print(f"    - {s}")
        else:
            print(f"  Message: {result.get('message')}")

asyncio.run(test())
