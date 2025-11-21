# How to Apply RPC Functions to Supabase

Since direct PostgreSQL connection has network limitations, follow these steps to apply the RPC functions via the Supabase SQL Editor:

## Step 1: Open Supabase SQL Editor

1. Go to: https://supabase.com/dashboard/project/ggevgecnnmcznurxhplu/sql/new
2. Or navigate to your project → SQL Editor → New Query

## Step 2: Copy and Run the SQL

1. Open the file: `supabase_rpc_functions.sql`
2. Copy ALL the contents (Ctrl+A, Ctrl+C)
3. Paste into the Supabase SQL Editor
4. Click "RUN" or press Ctrl+Enter

You should see: **Success. No rows returned**

## Step 3: Verify Functions Were Created

Run this query in the SQL Editor to list all functions:

```sql
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
    AND routine_type = 'FUNCTION'
    AND routine_name IN (
        'market_stats',
        'top_investors', 
        'owner_portfolio',
        'find_comparables',
        'transaction_velocity',
        'seasonal_patterns',
        'likely_sellers',
        'compare_communities',
        'property_history',
        'search_owners'
    )
ORDER BY routine_name;
```

You should see all 10 functions listed.

## Step 4: Test the Functions

After applying, run this command to test:

```bash
python test_rpc_functions.py
```

## Available RPC Functions

Once applied, these functions can be called via:
- Python: `supabase.rpc('function_name', { params })`
- REST API: `POST https://ggevgecnnmcznurxhplu.supabase.co/rest/v1/rpc/function_name`

### Function Reference:

1. **market_stats** - Get market statistics for a community/property type
2. **top_investors** - Find top investors by portfolio value
3. **owner_portfolio** - Get all properties owned by someone
4. **find_comparables** - Find comparable properties for CMA
5. **transaction_velocity** - Transaction volume trends over time
6. **seasonal_patterns** - Seasonal transaction patterns
7. **likely_sellers** - Properties owned for 3+ years (prospecting)
8. **compare_communities** - Compare multiple communities
9. **property_history** - Full transaction history for a property
10. **search_owners** - Search for owners by name/phone

## Troubleshooting

If functions fail to create:
- Make sure you're using the **service_role** key or logged in as project owner
- Check for syntax errors in the SQL output
- Try creating functions one at a time

## Next Steps

After functions are applied:
1. Test them with `python test_rpc_functions.py`
2. Move on to pgvector setup for semantic search
3. Build the CMA report generator
