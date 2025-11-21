# Embedding Generation Scripts

## `generate_embeddings.py`

### Purpose
Generates OpenAI text embeddings for property descriptions to enable semantic search functionality.

### Features
- ✅ Batch processing (100 properties per batch)
- ✅ Rate limiting to avoid API throttling
- ✅ Automatic retry on failure
- ✅ Progress tracking and statistics
- ✅ Cost estimation
- ✅ Natural language description generation

### Prerequisites

#### 1. Environment Variables
Create a `.env` file in the project root or set these variables:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=sk-proj-your_openai_key
```

#### 2. Python Dependencies
```bash
pip install openai requests python-dotenv
```

#### 3. Database Setup
Ensure the vector embeddings migration has been run:
```bash
# Run this SQL migration first
psql -f database/migrations/add_vector_embeddings.sql
```

### Usage

#### Basic Usage
```bash
python backend/scripts/generate_embeddings.py
```

#### With Environment Variable (PowerShell)
```powershell
$env:OPENAI_API_KEY = "sk-..."; python backend/scripts/generate_embeddings.py
```

#### With Environment Variable (Bash)
```bash
OPENAI_API_KEY=sk-... python backend/scripts/generate_embeddings.py
```

### Configuration

You can modify these constants in the script:

```python
EMBEDDING_MODEL = "text-embedding-ada-002"  # OpenAI model
EMBEDDING_DIMENSION = 1536                   # Vector dimensions
BATCH_SIZE = 100                             # Properties per batch
RATE_LIMIT_DELAY = 1                         # Seconds between batches
```

In the `main()` function, you can adjust the fetch limit:
```python
properties = fetch_properties_without_embeddings(limit=10000)  # Default: 10,000
```

To process ALL properties, change to a very high number:
```python
properties = fetch_properties_without_embeddings(limit=999999)
```

### How It Works

#### Step 1: Fetch Properties
Queries Supabase for properties without embeddings:
```sql
SELECT id, community, building, unit, type, bedrooms, bathrooms, size_sqft, last_price
FROM properties
WHERE description_embedding IS NULL
LIMIT 10000
```

#### Step 2: Generate Descriptions
Creates natural language descriptions from structured data:

**Input (structured data)**:
```json
{
  "id": 12345,
  "bedrooms": 3,
  "type": "Apartment",
  "building": "Marina Crown",
  "community": "Dubai Marina",
  "unit": "1203",
  "size_sqft": 1500,
  "last_price": 2500000
}
```

**Output (natural language)**:
```
"3 bedroom apartment in Marina Crown Dubai Marina unit 1203 with 1500 sqft priced at AED 2.50M"
```

#### Step 3: Generate Embeddings
Calls OpenAI API to create 1536-dimensional vectors:
```python
response = client.embeddings.create(
    model="text-embedding-ada-002",
    input=descriptions
)
embeddings = [item.embedding for item in response.data]
```

#### Step 4: Update Database
Stores embeddings and metadata:
```sql
UPDATE properties
SET description_embedding = [0.123, -0.456, ...],
    embedding_generated_at = NOW(),
    embedding_model = 'text-embedding-ada-002'
WHERE id = 12345
```

### Output Example

```
======================================================================
🤖 Property Embedding Generator
======================================================================

📊 Configuration:
   Embedding Model: text-embedding-ada-002
   Dimensions: 1536
   Batch Size: 100

🔍 Fetching properties without embeddings...
   Found 173343 properties to process

⚙️  Processing 1734 batches...

📦 Batch 1/1734 (100 properties)
   ✅ Success: 100, ❌ Failed: 0
   ⏳ Waiting 1s before next batch...

📦 Batch 2/1734 (100 properties)
   ✅ Success: 100, ❌ Failed: 0
   ⏳ Waiting 1s before next batch...

...

======================================================================
✅ Embedding Generation Complete!
======================================================================

📊 Results:
   Total Processed: 173343
   ✅ Successful: 173343
   ❌ Failed: 0
   Success Rate: 100.0%

💰 Estimated Cost: $0.8667 USD

🔍 Verifying embedding stats...
   Total Properties: 173343
   With Embeddings: 173343
   Coverage: 100.00%

======================================================================
🎉 Ready for semantic search!
======================================================================
```

### Cost Information

#### OpenAI Pricing (ada-002)
- **Rate**: $0.0001 per 1,000 tokens
- **Average property description**: ~50 tokens
- **Cost per property**: ~$0.000005 USD

#### Estimated Costs
| Properties | Cost (USD) |
|-----------|-----------|
| 1,000     | $0.005    |
| 10,000    | $0.05     |
| 100,000   | $0.50     |
| 173,343   | $0.87     |

### Performance

#### Processing Speed
- **Batch size**: 100 properties
- **Rate limit delay**: 1 second per batch
- **Throughput**: ~100 properties/second (OpenAI API)
- **Total time for 173K properties**: ~30-40 minutes

#### Database Impact
- Minimal during processing (100 UPDATEs per second)
- Index rebuild recommended after completion
- Storage: ~6KB per property (1536 floats × 4 bytes)

### Monitoring Progress

Check embedding status at any time:

```sql
-- Via RPC function
SELECT get_embedding_stats();

-- Direct query
SELECT 
    COUNT(*) as total,
    COUNT(description_embedding) as with_embeddings,
    ROUND(COUNT(description_embedding)::numeric / COUNT(*) * 100, 2) as coverage_pct
FROM properties;
```

### Troubleshooting

#### Error: "Column property_id does not exist"
**Cause**: Old version of script using wrong column name  
**Solution**: Update script to use `id` instead of `property_id`

#### Error: "OpenAI API key not set"
**Cause**: Missing or invalid OPENAI_API_KEY  
**Solution**: 
```powershell
$env:OPENAI_API_KEY = "sk-proj-..."
```

#### Error: "Failed to fetch properties: 400"
**Cause**: Database schema mismatch  
**Solution**: Check that column names match the database schema

#### Rate Limiting (429 errors)
**Cause**: Too many requests to OpenAI  
**Solution**: Increase `RATE_LIMIT_DELAY` from 1 to 2-3 seconds

#### Script Interrupted
**Solution**: Just re-run the script. It automatically skips properties that already have embeddings.

### Post-Generation Tasks

#### 1. Rebuild Index
After generating all embeddings, rebuild the index for optimal performance:
```sql
REINDEX INDEX idx_properties_description_embedding;
```

#### 2. Verify Coverage
```sql
SELECT get_embedding_stats();
```

#### 3. Test Semantic Search
```sql
SELECT * FROM semantic_search_properties(
    'luxury 3 bedroom apartment in Dubai Marina',
    10
);
```

### Advanced Usage

#### Process Specific Properties
Modify the fetch function to add filters:
```python
params = {
    "select": "id,community,building,...",
    "description_embedding": "is.null",
    "community": "eq.Dubai Marina",  # Add filter
    "limit": limit
}
```

#### Regenerate All Embeddings
```sql
-- Clear all embeddings
UPDATE properties SET description_embedding = NULL;

-- Then run script
python backend/scripts/generate_embeddings.py
```

#### Update Embeddings for Specific Properties
```sql
-- Clear embeddings for expensive properties
UPDATE properties 
SET description_embedding = NULL 
WHERE last_price > 10000000;

-- Script will regenerate only these
python backend/scripts/generate_embeddings.py
```

### Best Practices

1. **Run during off-peak hours** for large batch processing
2. **Monitor costs** - check OpenAI dashboard regularly
3. **Keep backups** before clearing embeddings
4. **Test on small batches** first (change limit to 100)
5. **Use service role key** for unrestricted access
6. **Monitor memory usage** for very large batches

### Integration with Search

Once embeddings are generated, use them with:

```sql
-- Semantic search function
SELECT * FROM semantic_search_properties(
    'affordable studio near JBR beach',
    20
) LIMIT 10;

-- Results include similarity scores
-- Higher score = better match (closer to 1.0)
```

### Maintenance Schedule

#### Weekly
- Check embedding coverage: `SELECT get_embedding_stats();`

#### Monthly
- Regenerate embeddings for properties with updated data
- Review and optimize index performance

#### As Needed
- Update to newer embedding models
- Adjust batch size based on usage patterns
- Scale rate limits based on OpenAI tier

---

**Last Updated**: November 11, 2025  
**Script Version**: 1.0  
**Compatible With**: OpenAI API v1.0+, Supabase (PostgreSQL + pgvector)
