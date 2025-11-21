"""Fix Serenia aliases - remove incorrect ones and add correct ones"""
import asyncio
from backend.supabase_client import select, upsert
from backend.supabase_client import get_client

async def fix_aliases():
    # Delete incorrect Serenia aliases
    print("Removing incorrect Serenia aliases...")
    client = await get_client()
    
    # Delete the bad aliases
    bad_aliases = ["Serenia", "Serenia Living", "Serenia Palm"]
    for alias in bad_aliases:
        try:
            response = await client.from_("aliases").delete().eq("alias", alias).execute()
            print(f"  ✓ Deleted: {alias}")
        except Exception as e:
            print(f"  ⚠ Could not delete {alias}: {e}")
    
    # Add correct aliases
    print("\nAdding correct Serenia aliases...")
    correct_aliases = [
        # Community aliases
        {"alias": "Serenia", "canonical": "SERENIA RESIDENCES THE PALM", "type": "community", "confidence": 0.95},
        {"alias": "Serenia Residences", "canonical": "SERENIA RESIDENCES THE PALM", "type": "community", "confidence": 1.0},
        {"alias": "Serenia Palm", "canonical": "SERENIA RESIDENCES THE PALM", "type": "community", "confidence": 0.9},
        
        # Building-specific aliases
        {"alias": "Serenia A", "canonical": "SERENIA RESIDENCES BUILDING A", "type": "building", "confidence": 0.95},
        {"alias": "Serenia Building A", "canonical": "SERENIA RESIDENCES BUILDING A", "type": "building", "confidence": 1.0},
        
        {"alias": "Serenia B", "canonical": "SERENIA RESIDENCES BUILDING B", "type": "building", "confidence": 0.95},
        {"alias": "Serenia Building B", "canonical": "SERENIA RESIDENCES BUILDING B", "type": "building", "confidence": 1.0},
        
        {"alias": "Serenia C", "canonical": "SERENIA RESIDENCES BUILDING C", "type": "building", "confidence": 0.95},
        {"alias": "Serenia Building C", "canonical": "SERENIA RESIDENCES BUILDING C", "type": "building", "confidence": 1.0},
    ]
    
    try:
        await upsert("aliases", correct_aliases)
        print(f"  ✓ Added {len(correct_aliases)} correct Serenia aliases")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("✓ Serenia aliases fixed!")
    print("\nCorrect usage:")
    print("  'Serenia' or 'Serenia Palm' → Community: SERENIA RESIDENCES THE PALM")
    print("  'Serenia A' → Building: SERENIA RESIDENCES BUILDING A")
    print("  'Serenia B' → Building: SERENIA RESIDENCES BUILDING B")
    print("  'Serenia C' → Building: SERENIA RESIDENCES BUILDING C")

asyncio.run(fix_aliases())
