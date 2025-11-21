"""Test the new aliases"""
import asyncio
import httpx

async def test():
    tests = [
        "Who owns 905 at Seven Palm?",
        "Who owns 905 at Marina?",
        "Who owns 905 at The Palm?",
        "Properties in JBR",
        "Properties in DIFC",
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in tests:
            print(f"\nTesting: '{query}'")
            
            # Parse query
            response = await client.post(
                "http://localhost:8787/api/tools/parse_query",
                json={"query": query}
            )
            parsed = response.json()
            entities = parsed.get('entities', {})
            print(f"  Parsed: {entities}")
            
            # For ownership queries, test lookup
            if "owns" in query.lower():
                response = await client.post(
                    "http://localhost:8787/api/tools/current_owner",
                    json=entities
                )
                result = response.json()
                if result.get('found'):
                    print(f"  ✓ Found: {result.get('owner_name')} at {result.get('building')}")
                elif result.get('ambiguous'):
                    print(f"  ⚠ Ambiguous: {len(result.get('suggestions', []))} options")
                else:
                    print(f"  ✗ Not found: {result.get('message')}")

asyncio.run(test())
