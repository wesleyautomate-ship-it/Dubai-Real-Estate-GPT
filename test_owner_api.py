"""Test the owner lookup API with different scenarios"""
import asyncio
import httpx

API_BASE = "http://localhost:8787/api"

async def test_owner_lookup():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Ambiguous query (just unit 905)
        print("Test 1: Ambiguous query - Who owns 905?")
        response = await client.post(
            f"{API_BASE}/tools/current_owner",
            json={"unit": "905"}
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Found: {result.get('found')}")
        print(f"Ambiguous: {result.get('ambiguous', False)}")
        if result.get('suggestions'):
            print(f"Suggestions: {len(result['suggestions'])} properties")
            for s in result['suggestions'][:3]:
                print(f"  - {s['unit']} at {s['building']} ({s['community']})")
        
        # Test 2: Specific query
        print("\nTest 2: Specific query - Who owns 905 at Marina Apartments 2?")
        response = await client.post(
            f"{API_BASE}/tools/current_owner",
            json={"unit": "905", "building": "Marina Apartments 2"}
        )
        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Found: {result.get('found')}")
        if result.get('found'):
            print(f"Owner: {result.get('owner_name')}")
            print(f"Phone: {result.get('owner_phone')}")
            print(f"Building: {result.get('building')}")
            print(f"Community: {result.get('community')}")
            print(f"Price: AED {result.get('last_price', 0):,.0f}")

if __name__ == "__main__":
    asyncio.run(test_owner_lookup())
