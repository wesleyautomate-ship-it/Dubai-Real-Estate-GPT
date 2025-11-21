# How to Apply Fixed Search Functions

## What Was Wrong?

The original search functions used **incorrect column names**:
- ❌ Used: `property_id`, `building_name`, `price_aed`, `property_type`  
- ✅ Actual: `id`, `building`, `last_price`, `type`

## How to Fix (2 Options)

### Option 1: Via Supabase Dashboard (Easiest)

1. **Open Supabase Dashboard** → Go to your project
2. **Click "SQL Editor"** in the left menu
3. **Open** `semantic_search_FIXED.sql` file on your computer
4. **Copy the entire contents** (Ctrl+A, Ctrl+C)
5. **Paste** into the SQL Editor
6. **Click "Run"** button
7. ✅ Done! Functions are now updated

### Option 2: Using psql CLI

```bash
# If you have psql installed
psql "your_supabase_connection_string" < database/functions/semantic_search_FIXED.sql
```

## What This Fixes

### 1. ✅ `search_properties_semantic()`
Now correctly returns:
- `id` (not property_id)
- `building` (not building_name)
- `last_price` (not price_aed)
- `type` (not property_type)
- Plus: `unit`, `bathrooms` (new!)

### 2. ✅ `find_similar_properties()`
Now takes `bigint` ID (not text)

### 3. ✅ `hybrid_property_search()`
Updated all column references

## Verify It Worked

After applying, run this in Supabase SQL Editor:

```sql
-- Check if functions exist
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
    AND routine_name LIKE '%properties%'
ORDER BY routine_name;
```

Should show:
- `find_similar_properties`
- `hybrid_property_search`
- `search_properties_semantic`

## About Those Tables/Views

### `chunks` (0 rows)
- Supabase auto-created table
- Not used in your schema
- **Can ignore** or delete

### `v_current_owner` (shows "-")
- This is a **VIEW** (not a table)
- Queries `transactions` table on-the-fly
- Shows current owner for each property
- **Working correctly!**

### `v_transaction_history` (shows "-")
- Also a **VIEW**
- Shows all transactions sorted by date
- **Working correctly!**

**Views don't store data** - they're like saved queries. The "-" is normal.

## Test After Embeddings Complete

Once embeddings are generated, test with:

```sql
-- Get a sample property ID
SELECT id FROM properties LIMIT 1;

-- Test find similar (use ID from above)
SELECT * FROM find_similar_properties(
    target_property_id := 12345,  -- Your property ID
    match_count := 5
);
```

## Next Steps

1. ✅ Apply these fixes now (Option 1)
2. ⏳ Wait for embeddings to complete (~123K remaining)
3. 🧪 Test search functions
4. 🚀 Build API/Frontend

---

**Need help?** The functions are now in `semantic_search_FIXED.sql` - just copy/paste into Supabase SQL Editor!
