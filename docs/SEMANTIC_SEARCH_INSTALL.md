# 🚀 Semantic Search Installation Guide

Complete step-by-step guide to enable AI-powered semantic property search in RealEstateGPT.

## 📋 What You'll Get

After completing this guide, your AI agent will be able to:
- ✅ **Natural language search**: "Find luxury 2BR apartments with sea view under 3M AED"
- ✅ **Semantic matching**: Finds properties even without exact keyword matches
- ✅ **Smart filters**: Combine AI search with traditional filters (price, bedrooms, location)
- ✅ **Similarity scoring**: Shows how relevant each property is to the search query

---

## 🎯 Prerequisites

- ✅ Supabase project with real estate data
- ✅ OpenAI API key (already configured)
- ✅ RealEstateGPT chat agent (already built)
- ⏳ pgvector extension (we'll enable this)

---

## 📊 Installation Steps

### STEP 1: Enable pgvector Extension (5 minutes)

#### Option A: Via Supabase Dashboard (Easiest)

1. Open https://app.supabase.com
2. Select your project
3. Go to **Database → Extensions** (left sidebar)
4. Search for **"vector"**
5. Click **Enable** button next to "vector"
6. Wait 10-15 seconds for installation

#### Option B: Via SQL Editor

1. Open **SQL Editor** in Supabase Dashboard
2. Run this command:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Verify installation:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

Expected output:
```
extname | extversion
--------|------------
vector  | 0.5.1
```

---

### STEP 2: Add Embedding Columns & Indexes (2 minutes)

1. Open **SQL Editor** in Supabase Dashboard
2. Copy the contents of: `database/migrations/add_vector_embeddings.sql`
3. Paste and run the SQL
4. Wait for completion (~30 seconds)

**What this does:**
- Adds `description_embedding` column (1536-dimensional vectors)
- Adds `image_embedding` column (for future image search)
- Creates IVFFlat indexes for fast similarity search
- Adds helper function `get_embedding_stats()`

**Verify it worked:**
```sql
SELECT get_embedding_stats();
```

Expected output:
```json
{
  "total_properties": 12345,
  "with_description_embedding": 0,
  "embedding_coverage_pct": 0.00
}
```
*(0% is normal at this stage)*

---

### STEP 3: Deploy Semantic Search RPC Functions (2 minutes)

1. Open **SQL Editor** in Supabase Dashboard
2. Copy the contents of: `database/functions/semantic_search.sql`
3. Paste and run the SQL
4. Wait for completion (~10 seconds)

**What this deploys:**
- `search_properties_semantic()` - Main semantic search function
- `find_similar_properties()` - Find properties similar to a given property
- `hybrid_property_search()` - Combines text + semantic search

**Verify deployment:**
```sql
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_name LIKE '%semantic%';
```

Expected output:
```
search_properties_semantic
find_similar_properties
hybrid_property_search
```

---

### STEP 4: Generate Embeddings for Properties (10-30 minutes)

This is the time-consuming step. We'll generate AI embeddings for all your properties.

#### 4.1: Check Configuration

Make sure your `.env` has:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=sk-your-openai-api-key
```

#### 4.2: Run the Embedding Generator

```powershell
cd "C:\Users\wesle\OneDrive\Desktop\Dubai Real Estate Database"
python backend\scripts\generate_embeddings.py
```

**What happens:**
- Fetches all properties without embeddings
- Generates natural language descriptions
- Sends descriptions to OpenAI for embedding (1536-dim vectors)
- Stores embeddings back in Supabase
- Processes in batches of 100 to avoid rate limits

**Example output:**
```
🤖 Property Embedding Generator
============================================================

📊 Configuration:
   Embedding Model: text-embedding-ada-002
   Dimensions: 1536
   Batch Size: 100

🔍 Fetching properties without embeddings...
   Found 2,547 properties to process

⚙️  Processing 26 batches...

📦 Batch 1/26 (100 properties)
   ✅ Success: 100, ❌ Failed: 0
   ⏳ Waiting 1s before next batch...

...

✅ Embedding Generation Complete!
============================================================

📊 Results:
   Total Processed: 2,547
   ✅ Successful: 2,547
   ❌ Failed: 0
   Success Rate: 100.0%

💰 Estimated Cost: $0.0127 USD

🎉 Ready for semantic search!
```

**Time estimate:**
- 1,000 properties: ~5-10 minutes
- 10,000 properties: ~30-60 minutes
- 100,000 properties: ~5-8 hours

**Cost estimate:**
- OpenAI ada-002: $0.0001 per 1K tokens
- Average property: ~50 tokens
- **1,000 properties**: ~$0.005 USD (half a cent!)
- **10,000 properties**: ~$0.05 USD (5 cents)

#### 4.3: Verify Embeddings

```powershell
# Check stats via RPC
python backend\scripts\call_check_pgvector.py
```

Or in SQL:
```sql
SELECT get_embedding_stats();
```

Expected output:
```json
{
  "total_properties": 2547,
  "with_description_embedding": 2547,
  "embedding_coverage_pct": 100.00,
  "latest_embedding_date": "2025-01-11T13:45:00Z"
}
```

---

### STEP 5: Test Semantic Search (2 minutes)

#### Test with Python:

```powershell
cd backend\core
python
```

```python
from tools import semantic_search

# Test 1: Natural language search
result = semantic_search(
    query="luxury waterfront apartment with pool",
    limit=5
)
print(f"Found {result['count']} properties")
print(result['properties'][0])

# Test 2: With filters
result = semantic_search(
    query="family-friendly 2BR near schools",
    limit=10,
    filter_bedrooms=2,
    filter_max_price=2000000
)
print(f"Found {result['count']} properties")
```

#### Test with RealEstateGPT:

```powershell
cd backend\api
python chat_api.py
```

Try these queries:
- "Find me luxury apartments with sea view"
- "I want a family-friendly property near good schools"
- "Show me waterfront properties with amenities under 5 million"
- "Find properties similar to luxury penthouses in Dubai Marina"

---

## ✅ Verification Checklist

Before moving to production, verify:

- [ ] pgvector extension enabled (`SELECT * FROM pg_extension WHERE extname = 'vector'`)
- [ ] Embedding columns exist (`\d properties` in psql or check schema)
- [ ] Indexes created (`SELECT * FROM pg_indexes WHERE indexname LIKE '%embedding%'`)
- [ ] RPC functions deployed (`SELECT * FROM information_schema.routines WHERE routine_name LIKE '%semantic%'`)
- [ ] Embeddings generated (`SELECT COUNT(*) FROM properties WHERE description_embedding IS NOT NULL`)
- [ ] Embedding coverage > 95% (`SELECT get_embedding_stats()`)
- [ ] Semantic search returns results (test with Python)
- [ ] RealEstateGPT agent can use semantic_search tool

---

## 🎯 Using Semantic Search

### In RealEstateGPT Agent

The agent now has a 6th tool: `semantic_search`

**Example user queries that trigger it:**
- "Find luxury properties with modern amenities"
- "Show me family-friendly apartments"
- "I want something like a penthouse but cheaper"
- "Find properties with a view"

**Behind the scenes:**
1. User asks: "Find luxury waterfront apartments"
2. Agent calls `semantic_search(query="luxury waterfront apartments")`
3. OpenAI generates embedding for the query
4. Supabase searches properties by vector similarity
5. Returns top matching properties with similarity scores
6. Agent formats results conversationally

### Direct API Usage

```python
from backend.core.tools import semantic_search

# Basic search
results = semantic_search(
    query="affordable 2BR apartments near metro",
    limit=10
)

# With filters
results = semantic_search(
    query="luxury penthouse with panoramic views",
    limit=5,
    filter_community="Dubai Marina",
    filter_min_price=5000000,
    filter_max_price=15000000,
    filter_bedrooms=3,
    match_threshold=0.75  # Higher = more strict
)

# Process results
for prop in results['properties']:
    print(f"{prop['community']} - {prop['bedrooms']}BR")
    print(f"Price: AED {prop['price_aed']:,.0f}")
    print(f"Similarity: {prop['similarity']:.2%}")
    print()
```

---

## 🔧 Maintenance

### Regenerate Embeddings (when needed)

Run embeddings script again when:
- You add new properties to the database
- Property descriptions change significantly
- You want to use a newer embedding model

```powershell
python backend\scripts\generate_embeddings.py
```

The script automatically skips properties that already have embeddings.

### Update Embeddings for Specific Properties

```python
from backend.scripts.generate_embeddings import (
    generate_property_description,
    generate_embeddings,
    update_property_embedding
)

# Get property
prop = {"property_id": "PROP123", "community": "Dubai Marina", ...}

# Generate embedding
desc = generate_property_description(prop)
embedding = generate_embeddings([desc])[0]

# Update
update_property_embedding(prop['property_id'], embedding)
```

### Monitor Performance

```sql
-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%';

-- Check embedding coverage by community
SELECT 
    community,
    COUNT(*) as total,
    COUNT(description_embedding) as with_embedding,
    ROUND(COUNT(description_embedding)::numeric / COUNT(*) * 100, 2) as coverage_pct
FROM properties
GROUP BY community
ORDER BY total DESC
LIMIT 20;
```

---

## 💰 Cost Analysis

### One-Time Setup Costs
- **Initial embeddings** (10,000 properties): ~$0.50 USD
- **pgvector**: Free (included in Supabase)
- **Storage**: ~60KB per 1,000 properties (negligible)

### Ongoing Costs
- **New property embeddings**: ~$0.00005 per property
- **Search queries**: ~$0.0001 per search
- **1,000 searches/month**: ~$0.10 USD

**Total monthly cost for active use**: < $1 USD

---

## 🐛 Troubleshooting

### "pgvector extension not found"
**Solution**: Go back to Step 1, enable pgvector extension

### "Function search_properties_semantic does not exist"
**Solution**: Go back to Step 3, deploy the RPC functions

### "Column description_embedding does not exist"
**Solution**: Go back to Step 2, run the migration SQL

### "No properties have embeddings"
**Solution**: Run `python backend/scripts/generate_embeddings.py`

### "Semantic search returns 0 results"
**Possible causes:**
1. No embeddings generated yet → Run embedding script
2. match_threshold too high (try 0.5 instead of 0.7)
3. Filters too restrictive → Remove some filters
4. Query too specific → Try broader query

### "Slow search performance"
**Solutions:**
1. Check indexes exist: `SELECT * FROM pg_indexes WHERE indexname LIKE '%embedding%'`
2. Increase lists parameter if you have >100K properties
3. Add more specific filters (community, price range)
4. Consider upgrading Supabase plan for more resources

---

## 🎉 Success!

You now have **AI-powered semantic search** integrated into your Real Estate platform!

**What's next?**
- Test with real user queries
- Fine-tune match_threshold for your use case
- Add more property metadata for better embeddings
- Explore hybrid search (text + semantic)
- Consider image embeddings for visual search

---

## 📚 Additional Resources

- **pgvector Docs**: https://github.com/pgvector/pgvector
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Supabase Vector**: https://supabase.com/docs/guides/ai/vector-embeddings
- **Example Queries**: See `docs/SEMANTIC_SEARCH_EXAMPLES.md`

---

**Created**: January 2025  
**Status**: Production Ready  
**Next Review**: After testing with users
