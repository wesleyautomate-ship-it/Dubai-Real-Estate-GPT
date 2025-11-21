# 🔍 Checking & Enabling pgvector on Supabase

## What is pgvector?

**pgvector** is a PostgreSQL extension that adds support for vector similarity search. It's essential for:
- **AI/ML embeddings storage** (OpenAI, Cohere, etc.)
- **Semantic search** (find similar text/properties)
- **Recommendation systems** (similar properties)
- **Image similarity** (reverse image search)

## Why You Need It for RealEstateGPT

With pgvector enabled, you can:
1. **Store property description embeddings** from OpenAI
2. **Semantic property search** - "Find properties similar to this one"
3. **Smart recommendations** - "Properties like this but cheaper"
4. **Multi-modal search** - Search by image or description

---

## Quick Check (3 Steps)

### Step 1: Create the RPC Function

1. Open **Supabase Dashboard**: https://app.supabase.com
2. Navigate to: **SQL Editor** (left sidebar)
3. Copy and paste this SQL:

```sql
-- database/functions/check_pgvector.sql

CREATE OR REPLACE FUNCTION public.check_pgvector()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result jsonb;
    ext_record record;
    avail_record record;
    vector_cols int;
BEGIN
    result := jsonb_build_object(
        'timestamp', now(),
        'database', current_database(),
        'pgvector_installed', false,
        'pgvector_version', null,
        'pgvector_available', false,
        'available_version', null,
        'vector_type_exists', false,
        'vector_columns_count', 0,
        'vector_operators', jsonb_build_array()
    );
    
    SELECT extname, extversion INTO ext_record
    FROM pg_extension
    WHERE extname = 'vector';
    
    IF FOUND THEN
        result := jsonb_set(result, '{pgvector_installed}', 'true'::jsonb);
        result := jsonb_set(result, '{pgvector_version}', to_jsonb(ext_record.extversion));
    END IF;
    
    SELECT name, default_version, installed_version INTO avail_record
    FROM pg_available_extensions
    WHERE name = 'vector';
    
    IF FOUND THEN
        result := jsonb_set(result, '{pgvector_available}', 'true'::jsonb);
        result := jsonb_set(result, '{available_version}', to_jsonb(avail_record.default_version));
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
        result := jsonb_set(result, '{vector_type_exists}', 'true'::jsonb);
    END IF;
    
    SELECT count(*) INTO vector_cols
    FROM information_schema.columns
    WHERE udt_name = 'vector';
    
    result := jsonb_set(result, '{vector_columns_count}', to_jsonb(vector_cols));
    
    IF result->>'pgvector_installed' = 'true' THEN
        result := jsonb_set(result, '{vector_operators}', (
            SELECT jsonb_agg(oprname ORDER BY oprname)
            FROM pg_operator
            WHERE oprleft = (SELECT oid FROM pg_type WHERE typname = 'vector')
               OR oprright = (SELECT oid FROM pg_type WHERE typname = 'vector')
            LIMIT 10
        ));
    END IF;
    
    RETURN result;
END;
$$;

GRANT EXECUTE ON FUNCTION public.check_pgvector() TO anon, authenticated, service_role;
```

4. Click **Run** (or press F5)
5. You should see: "Success. No rows returned"

### Step 2: Run the Check Script

```powershell
cd "C:\Users\wesle\OneDrive\Desktop\Dubai Real Estate Database"
python backend\scripts\call_check_pgvector.py
```

### Step 3: Read the Results

You'll see one of these outcomes:

#### ✅ Scenario A: pgvector INSTALLED
```
✅ STATUS: pgvector is FULLY OPERATIONAL

🎉 You can use pgvector features:
   - Store vector embeddings
   - Semantic similarity search
   - Cosine/L2 distance calculations
```
**Action**: Nothing needed! You're ready to use pgvector.

#### ⚠️ Scenario B: pgvector AVAILABLE but NOT ENABLED
```
⚠️ STATUS: pgvector AVAILABLE but NOT ENABLED

📋 To enable pgvector:
   1. Go to Supabase Dashboard
   2. Database → Extensions
   3. Search 'vector' and click 'Enable'
```
**Action**: Follow the steps below to enable it.

#### ❌ Scenario C: pgvector NOT AVAILABLE
```
❌ STATUS: pgvector NOT AVAILABLE

⚠️ Your Supabase instance doesn't have pgvector available.
```
**Action**: Contact Supabase support or check your plan.

---

## How to Enable pgvector

### Method 1: Supabase Dashboard (Easiest)

1. Open **Supabase Dashboard**: https://app.supabase.com
2. Select your project: **dubai-realestate** (or similar)
3. Navigate to: **Database → Extensions** (left sidebar)
4. Search for: **"vector"** or **"pgvector"**
5. Click: **Enable** button
6. Wait 5-10 seconds for installation
7. Run the check script again to verify

### Method 2: SQL Editor

1. Open **SQL Editor** in Supabase Dashboard
2. Run this command:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Verify installation:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

You should see:
```
extname | extversion
--------|------------
vector  | 0.5.1 (or similar)
```

---

## Using pgvector in Your Real Estate App

### 1. Add Embedding Columns

Add vector columns to store embeddings:

```sql
-- For property descriptions (OpenAI ada-002 = 1536 dimensions)
ALTER TABLE properties 
ADD COLUMN description_embedding vector(1536);

-- For property images (CLIP embeddings = 512 dimensions)
ALTER TABLE properties 
ADD COLUMN image_embedding vector(512);

-- Create indexes for fast similarity search
CREATE INDEX ON properties 
USING ivfflat (description_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX ON properties 
USING ivfflat (image_embedding vector_cosine_ops)
WITH (lists = 100);
```

### 2. Generate Embeddings with OpenAI

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Generate embedding for property description
description = "Luxury 2BR apartment in Downtown Dubai with Burj Khalifa view"
response = client.embeddings.create(
    model="text-embedding-ada-002",
    input=description
)
embedding = response.data[0].embedding  # 1536-dim vector

# Store in database
supabase.table("properties").update({
    "description_embedding": embedding
}).eq("id", property_id).execute()
```

### 3. Semantic Property Search

```sql
-- Find properties similar to a given property
SELECT 
    property_id,
    community,
    bedrooms,
    price_aed,
    1 - (description_embedding <=> (
        SELECT description_embedding 
        FROM properties 
        WHERE property_id = 'PROP123'
    )) AS similarity
FROM properties
WHERE description_embedding IS NOT NULL
ORDER BY description_embedding <=> (
    SELECT description_embedding 
    FROM properties 
    WHERE property_id = 'PROP123'
)
LIMIT 10;
```

### 4. Natural Language Property Search

```python
def semantic_search(query: str, limit: int = 10):
    """
    Search properties using natural language
    Example: "affordable 2BR near metro with pool"
    """
    # Generate embedding for search query
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    query_embedding = response.data[0].embedding
    
    # Search using cosine similarity
    result = supabase.rpc('search_properties_semantic', {
        'query_embedding': query_embedding,
        'match_threshold': 0.7,
        'match_count': limit
    }).execute()
    
    return result.data
```

### 5. Create Search RPC Function

```sql
CREATE OR REPLACE FUNCTION search_properties_semantic(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    property_id text,
    community text,
    bedrooms int,
    price_aed numeric,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.property_id,
        p.community,
        p.bedrooms,
        p.price_aed,
        1 - (p.description_embedding <=> query_embedding) AS similarity
    FROM properties p
    WHERE p.description_embedding IS NOT NULL
        AND 1 - (p.description_embedding <=> query_embedding) > match_threshold
    ORDER BY p.description_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

## Integration with RealEstateGPT

Add a new tool to `backend/core/tools.py`:

```python
def semantic_search(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search properties using semantic similarity
    
    Args:
        query: Natural language search query
        limit: Max results to return
    
    Returns:
        List of similar properties with scores
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Generate embedding
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    query_embedding = response.data[0].embedding
    
    # Search via Supabase
    url = f"{SUPABASE_URL}/rest/v1/rpc/search_properties_semantic"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query_embedding": query_embedding,
        "match_threshold": 0.7,
        "match_count": limit
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if resp.status_code == 200:
        results = resp.json()
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "properties": results
        }
    else:
        return {"success": False, "error": resp.text}
```

Add to OpenAI tool schemas:

```python
{
    "type": "function",
    "function": {
        "name": "semantic_search",
        "description": "Search properties using natural language (semantic similarity)",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query, e.g. 'luxury 2BR with sea view'"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
}
```

---

## Cost Considerations

### OpenAI Embeddings (ada-002)
- **Price**: $0.0001 per 1K tokens (~$0.0001 per property)
- **Dimension**: 1536
- **Best for**: Text descriptions

### Example Costs:
- **1,000 properties**: ~$0.10 (one-time)
- **1,000 searches/month**: ~$0.10/month
- **Total**: Very affordable!

---

## Troubleshooting

### Error: "function check_pgvector() does not exist"
**Solution**: Run the SQL from Step 1 in Supabase SQL Editor

### Error: "permission denied for extension vector"
**Solution**: Use service_role key, not anon key

### Error: "could not load library vector"
**Solution**: pgvector not installed. Follow "How to Enable pgvector" section

### Slow similarity searches
**Solution**: Create indexes (see "Add Embedding Columns" section)

---

## Next Steps

1. ✅ **Verify pgvector** (run check script)
2. ✅ **Enable if needed** (Supabase Dashboard)
3. 📝 **Add embedding columns** (run migration SQL)
4. 🤖 **Generate embeddings** (OpenAI API)
5. 🔍 **Test semantic search** (try queries)
6. 🔧 **Integrate with agent** (add tool to RealEstateGPT)

---

## Resources

- **pgvector Docs**: https://github.com/pgvector/pgvector
- **Supabase Vector Guide**: https://supabase.com/docs/guides/ai/vector-embeddings
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Similarity Search**: https://supabase.com/docs/guides/ai/vector-indexes

---

**Created**: January 2025  
**Status**: Ready for implementation  
**Priority**: Optional (but highly recommended for AI features)
