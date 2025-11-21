# Community Structure Restructuring Guide

## The Problem

**Current Issue:**
- `community` column contains **sub-communities/building names** (e.g., "BALQIS RESIDENCE", "SERENIA RESIDENCES")
- Should contain **master community** from filename (e.g., "Palm Jumeirah", "City Walk")

**Example:**
```
File: Palm Jumeirah Jan 2025.xlsx
Current community: "BALQIS RESIDENCE"  ❌ Wrong
Should be: "Palm Jumeirah"  ✅ Correct
```

## The Solution

### New Structure:
- **`master_community`**: Top-level community from filename (Palm Jumeirah, City Walk, etc.)
- **`sub_community`**: Building complex/sub-area (Balqis Residence, Serenia Residences, etc.)
- **`building`**: Specific building name (BALQIS RESIDENCE 2, SERENIA BUILDING A, etc.)
- **`community`**: Keep as-is for backwards compatibility

### Hierarchy:
```
Master Community: Palm Jumeirah (from filename)
  └─ Sub-Community: Serenia Residences (current "community" value)
      └─ Building: SERENIA RESIDENCES BUILDING A (specific building)
          └─ Unit: 905
```

## Impact on Embeddings

✅ **SAFE**: Adding columns and populating them does NOT affect existing embeddings.
- Embeddings are in `description_embedding` column
- We're only adding metadata columns
- No need to regenerate embeddings

## How to Apply

### Step 1: Run the SQL Migration

1. Go to Supabase SQL Editor: https://supabase.com/dashboard/project/ggevgecnnmcznurxhplu/sql/new
2. Copy contents of `database/restructure_communities.sql`
3. Paste and click **Run**

The script will:
1. Add `master_community` and `sub_community` columns
2. Copy current `community` → `sub_community`
3. Extract master community from `source_file` (e.g., "Palm Jumeirah Jan 2025.xlsx" → "Palm Jumeirah")
4. Create indexes for fast lookups
5. Update both `transactions` and `properties` tables

### Step 2: Verify the Changes

Run this to check results:

```python
python check_community_structure.py
```

Expected output:
```
Source File                    | Master Community | Sub-Community              | Building
Palm Jumeirah Jan 2025.xlsx    | Palm Jumeirah    | BALQIS RESIDENCE          | BALQIS RESIDENCE 2
Palm Jumeirah Jan 2025.xlsx    | Palm Jumeirah    | SERENIA RESIDENCES        | SERENIA BUILDING C
City Walk Jan 2025.xlsx        | City Walk        | City Walk                 | Castleton
```

## After Migration

### Update Your Code

**Before:**
```python
filters={"community": "ilike.%Marina%"}  # Was matching sub-communities
```

**After:**
```python
# Search by master community
filters={"master_community": "ilike.%Palm Jumeirah%"}

# Or search by sub-community  
filters={"sub_community": "ilike.%Serenia%"}

# Or both
filters={
    "master_community": "Palm Jumeirah",
    "sub_community": "ilike.%Serenia%"
}
```

### Update Aliases

The aliases table should also be updated:

```python
# Community aliases should map to master_community
"Palm" → "Palm Jumeirah" (master community)
"The Palm" → "Palm Jumeirah" (master community)

# Sub-community aliases
"Serenia" → "SERENIA RESIDENCES THE PALM" (sub-community)
```

### Update API Endpoints

In `backend/api/chat_tools_api.py`, update the resolve function to check both:

```python
async def resolve_name_via_aliases(name: str, name_type: str = None) -> tuple:
    """Returns (master_community, sub_community) tuple"""
    # Check if it's a master community alias
    # Check if it's a sub-community alias
    # Return appropriate values
```

## Benefits

1. **Clearer Hierarchy**: Palm Jumeirah → Serenia → Building A → Unit 905
2. **Better Filtering**: Search by master community or drill down to sub-community
3. **Accurate Context**: Chat can say "in Palm Jumeirah's Serenia Residences"
4. **Matches Data Source**: Community names match Excel filenames
5. **No Breaking Changes**: Old `community` column still exists

## Backwards Compatibility

The old `community` column is **NOT deleted**, so existing code will still work. You can migrate gradually:

- Phase 1: Add new columns (this migration)
- Phase 2: Update application code to use `master_community`
- Phase 3: Eventually deprecate old `community` column

## Master Communities in Your Database

Based on Excel files:
- Al Barari
- Arabian Ranches 1,2,3
- Arjan
- Bluewater
- Business Bay
- City Walk
- Damac Hills 1
- Damac Hills 2
- Damac Lagoon
- Downtown
- Palm Jumeirah
- Town Square
- (and more...)

## Example Queries After Migration

**Find all properties in Palm Jumeirah:**
```python
properties = await select(
    "transactions",
    select_fields="*",
    filters={"master_community": "Palm Jumeirah"},
    limit=100
)
```

**Find properties in Serenia within Palm Jumeirah:**
```python
properties = await select(
    "transactions",
    select_fields="*",
    filters={
        "master_community": "Palm Jumeirah",
        "sub_community": "ilike.%Serenia%"
    },
    limit=100
)
```

**User asks "Who owns 905 at Serenia in Palm Jumeirah?":**
```python
# System can now properly filter by both levels
result = await select(
    "transactions",
    select_fields="*",
    filters={
        "unit": "905",
        "master_community": "Palm Jumeirah",
        "sub_community": "ilike.%Serenia%"
    }
)
```

## Questions?

This restructuring:
- ✅ Does NOT affect embeddings
- ✅ Does NOT break existing code (old column still exists)
- ✅ Provides clearer data hierarchy
- ✅ Matches your Excel source structure
