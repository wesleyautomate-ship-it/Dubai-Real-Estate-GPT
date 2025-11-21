# Community Metadata Setup Guide

This guide explains how to add the community metadata to your database.

## What This Adds

Rich community information for 21 Dubai communities including:
- **Type**: Luxury, Mid-market, Affordable
- **Property Types**: Villas, Apartments, Townhouses
- **Pricing**: Average sale prices and rental rates
- **Demographics**: Target residents
- **Infrastructure**: Nearby amenities, schools, malls
- **Rental Yields**: ROI percentages
- **Service Charges**: Maintenance costs

## Step 1: Create the Database Table

### Option A: Using Supabase Dashboard (Recommended)
1. Go to your Supabase dashboard: https://supabase.com/dashboard/project/ggevgecnnmcznurxhplu
2. Click **SQL Editor** in the left sidebar
3. Click **New query**
4. Copy the contents of `database/create_community_metadata_table.sql`
5. Paste and click **Run**

### Option B: Using Command Line
```bash
# If you have psql installed
psql $DATABASE_URL -f database/create_community_metadata_table.sql
```

## Step 2: Import the Data

Run the import script:

```bash
python import_community_metadata.py
```

Expected output:
```
Loading community metadata from JSON...
Found 21 communities to import

Importing to database...
  ✓ Imported batch 1 (10 communities)
    - Al Barari: Luxury (exclusive villa enclave)
    - Al Barsha: Mid-market (established residential)
  ...

✓ Import complete!
  - Successfully imported: 21
  - Errors: 0
```

## Step 3: Verify Import

Check that data was imported correctly:

```python
python -c "import asyncio; from backend.supabase_client import select; result = asyncio.run(select('community_metadata', select_fields='community,type', filters={}, limit=5)); print(f'Found {len(result)} communities:'); [print(f'  - {r[\"community\"]}: {r[\"type\"]}') for r in result]"
```

## Communities Included

1. **Al Barari** - Luxury villa enclave
2. **Al Barsha** - Mid-market residential
3. **Arabian Ranches** - Gated villa community
4. **Bluewaters Island** - Waterfront luxury
5. **Business Bay** - Urban mixed-use
6. **City Walk** - Luxury lifestyle district
7. **Downtown Dubai** - Flagship urban center
8. **Dubai Hills Estate** - Golf community
9. **Dubai Marina** - Waterfront high-rises
10. **Emirates Hills** - Ultra-luxury villas
11. **International City** - Budget-friendly
12. **JBR** - Beachfront high-rise
13. **JLT** - Mixed-use towers
14. **JVC** - Family-friendly
15. **Mirdif** - Suburban villas
16. **Palm Jumeirah** - Exclusive island
17. **Dubai Silicon Oasis** - Tech park community
18. **Dubai Sports City** - Sports-themed
19. **Town Square** - Affordable suburban
20. **Umm Suqeim** - Coastal villa area

## How to Use in Your Application

### Example 1: Get Community Info
```python
from backend.supabase_client import select

# Get info for a specific community
info = await select(
    "community_metadata",
    select_fields="*",
    filters={"community": "Palm Jumeirah"},
    limit=1
)

print(f"Type: {info[0]['type']}")
print(f"Avg Price: {info[0]['avg_price_sale']}")
print(f"Rental Yield: {info[0]['rental_yield']}")
```

### Example 2: Filter by Budget
```python
# Get affordable communities (high rental yield)
affordable = await select(
    "community_metadata",
    select_fields="community,type,rental_yield,avg_price_sale",
    filters={"type": "ilike.%Affordable%"},
    limit=10
)
```

### Example 3: Enhance Search Results
When showing search results, join with community_metadata to show:
- Price ranges
- Demographics
- Rental yields
- Nearby infrastructure

## API Integration

You can create a new endpoint in `backend/api/community_api.py`:

```python
@router.get("/community/{name}")
async def get_community_info(name: str):
    """Get detailed information about a community"""
    result = await select(
        "community_metadata",
        select_fields="*",
        filters={"community": f"ilike.%{name}%"},
        limit=1
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Community not found")
    
    return result[0]
```

## Benefits

1. **Smart Recommendations**: Suggest communities based on budget/lifestyle
2. **Rich Search Results**: Show demographics, pricing, yields
3. **Market Insights**: Compare rental yields across communities
4. **Better Filtering**: Filter by property type, price range, demographics
5. **User Experience**: Help users discover suitable communities

## Maintenance

To update community data:
1. Edit `community_metadata.json`
2. Run `python import_community_metadata.py` again
3. The `upsert` will update existing records

## Troubleshooting

**Error: "relation community_metadata does not exist"**
- Solution: Run Step 1 first to create the table

**Error: "duplicate key value violates unique constraint"**
- Solution: The community already exists. The script will update it automatically with upsert.

**Import shows 0 successes**
- Check that `community_metadata.json` is in the current directory
- Verify your Supabase credentials in `.env`
