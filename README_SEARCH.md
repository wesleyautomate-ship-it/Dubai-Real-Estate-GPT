# 🏠 Dubai Real Estate Semantic Search Engine

Complete semantic property search system with OpenAI embeddings and Supabase pgvector.

## 📋 Overview

This system provides:
- ✅ **REST API** with semantic search, property details, and statistics endpoints
- ✅ **Web Interface** for natural language property queries
- ✅ **OpenAI Embeddings** (text-embedding-3-small) for semantic matching
- ✅ **Supabase pgvector** for fast vector similarity search
- ✅ **Dual storage**: chunks table + properties.description_embedding
- ✅ **Owner information** from transactions table
- ✅ **Rate limiting** and CORS for production readiness

## 🚀 Quick Start

### Step 1: Apply Database Migrations

In Supabase SQL Editor, run these files in order:

```sql
-- 1. Create chunks table
\i database/migrations/create_chunks_table.sql

-- 2. Add embedding columns to properties
\i database/migrations/add_property_embeddings.sql

-- 3. Create RPC functions
\i database/functions/search_rpcs.sql
```

Or use the convenience file:
```sql
\i sql/create_rpc.sql
```

After running migrations:
```sql
-- Analyze tables for optimal query performance
ANALYZE chunks;
ANALYZE properties;
```

### Step 2: Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
```

### Step 3: Configure Environment

Your `.env` file should already have:
```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_KEY
OPENAI_API_KEY=sk-...
API_PORT=8787
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIM=1536
```

### Step 4: Populate Embeddings

```powershell
# Generate embeddings for properties (recommended)
python backend/scripts/populate_chunks.py

# Alternative: populate properties table directly
python backend/scripts/populate_property_embeddings.py
```

Expected output:
```
🤖 Populating Chunks with Embeddings
====================================
📊 Fetching properties from Supabase...
   Found 1,234 properties

⚙️  Processing 13 batches...
📦 Batch 1/13 (100 properties)
   ✅ Generated 100 embeddings
   ✅ Inserted 100 chunks
   
...

✅ Complete! Inserted 1,234 chunks in 45s
💰 Estimated cost: $0.05 USD
```

### Step 5: Start the Server

```powershell
python run_server.py
```

Output:
```
======================================================================
🏠 Dubai Real Estate Semantic Search API
======================================================================

📡 Starting server at http://0.0.0.0:8787
📚 API Documentation: http://0.0.0.0:8787/api/docs
🔍 Search UI: http://0.0.0.0:8787/

======================================================================

INFO:     Started server process
INFO:     Waiting for application startup.
🚀 Starting Dubai Real Estate Search API...
📡 API will be available at http://0.0.0.0:8787
✅ Supabase client initialized
✅ Database connected - 1234 properties
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8787
```

### Step 6: Test the Search

Open http://localhost:8787 in your browser and try:
- "3 bedroom apartment in Dubai Marina"
- "Luxury penthouse with sea view"
- "Affordable studio near metro"
- "Two-bed apartment in City Walk under 3M AED"

## 📡 API Endpoints

### GET /api/search

Semantic property search with natural language queries.

**Parameters:**
- `q` (required): Search query (1-500 chars)
- `community` (optional): Filter by community name
- `min_size` / `max_size` (optional): Size range in sqft
- `bedrooms` (optional): Number of bedrooms
- `min_price` / `max_price` (optional): Price range in AED
- `limit` (optional): Max results (default 12, max 50)
- `threshold` (optional): Similarity threshold 0-1 (default 0.70)

**Example:**
```bash
curl "http://localhost:8787/api/search?q=3%20bedroom%20apartment%20in%20Dubai%20Marina&limit=5"
```

**Response:**
```json
{
  "results": [
    {
      "property_id": 123,
      "chunk_id": 456,
      "score": 0.892,
      "community": "Dubai Marina",
      "building": "Marina Heights",
      "unit": "1504",
      "bedrooms": 3,
      "size_sqft": 1850,
      "price_aed": 2500000,
      "owner_name": "Ahmed Mohammed",
      "owner_phone": "971501234567",
      "snippet": "3 bedroom luxury apartment in Marina Heights..."
    }
  ],
  "query": "3 bedroom apartment in Dubai Marina",
  "total": 5,
  "timing_ms": 234.5
}
```

### GET /api/properties/{id}

Get detailed property information.

**Example:**
```bash
curl "http://localhost:8787/api/properties/123"
```

**Response:**
```json
{
  "property": {
    "id": 123,
    "community": "Dubai Marina",
    "building": "Marina Heights",
    "unit": "1504",
    "bedrooms": 3,
    "size_sqft": 1850,
    "last_price": 2500000
  },
  "current_owner": {
    "name": "Ahmed Mohammed",
    "phone": "971501234567",
    "purchase_date": "2024-03-15",
    "purchase_price": 2500000
  },
  "transaction_history": [...],
  "total_transactions": 3
}
```

### GET /api/stats

Database statistics and embedding coverage.

**Example:**
```bash
curl "http://localhost:8787/api/stats"
```

**Response:**
```json
{
  "total_properties": 1234,
  "avg_price_per_sqft": 1450.25,
  "chunks_count": 1234,
  "properties_with_embeddings": 1234,
  "chunks_with_embeddings": 1234,
  "last_update": "2025-01-11T14:30:00Z",
  "embedding_coverage": {
    "properties_pct": 100.0,
    "chunks_pct": 100.0
  }
}
```

## 🗄️ Database Schema

### chunks Table

Stores text embeddings for semantic search.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| content | TEXT | Natural language property description |
| embedding | vector(1536) | OpenAI embedding |
| property_id | BIGINT | FK to properties |
| chunk_type | TEXT | Type of chunk (default: 'property_description') |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMPTZ | Creation timestamp |

**Indexes:**
- `idx_chunks_property_id` on property_id
- `idx_chunks_embedding` (IVFFLAT) on embedding

### properties Table (Extended)

Added columns:
- `description_embedding` vector(1536) - Property embedding
- `embedding_model` TEXT - Model name
- `embedding_generated_at` TIMESTAMPTZ - Generation time

**Index:**
- `idx_properties_embedding` (IVFFLAT) on description_embedding

### RPC Functions

**semantic_search_chunks**: Search chunks with filters  
**semantic_search_properties**: Search properties directly  
**db_stats**: Database statistics  
**semantic_search**: Backward-compatible alias

## 🔧 Data Population Scripts

### populate_chunks.py

Generates embeddings for all properties and inserts into chunks table.

**What it does:**
1. Fetches properties from Supabase (batch: 100)
2. Composes natural language descriptions
3. Generates OpenAI embeddings (batch: 100)
4. Inserts chunks with embeddings
5. Shows progress and stats

**Run:**
```powershell
python backend/scripts/populate_chunks.py
```

**Content template:**
```
{bedrooms} bedroom {property_type} in {building} {community} 
unit {unit} with {size_sqft} sqft priced at AED {price}M
```

### populate_property_embeddings.py

Alternative: populates properties.description_embedding directly.

**Run:**
```powershell
python backend/scripts/populate_property_embeddings.py
```

## 🎯 Testing

### Automated Tests

```powershell
python backend/scripts/test_queries.py
```

Tests these queries:
- "3 bedroom apartment in Dubai Marina"
- "Luxury penthouse with sea view"
- "Affordable studio near metro"
- "Two-bed apartment in City Walk under 3M AED"

### Manual Testing

1. **Browser**: http://localhost:8787
2. **API Docs**: http://localhost:8787/api/docs
3. **Health Check**: http://localhost:8787/health

## 🛠️ Troubleshooting

### Issue: 401 Unauthorized from Supabase

**Cause:** Wrong API key or URL

**Solution:**
```powershell
# Verify environment variables
echo $env:SUPABASE_URL
echo $env:SUPABASE_SERVICE_ROLE_KEY

# Re-run server
python run_server.py
```

### Issue: OpenAI Rate Limit Errors

**Cause:** Too many embedding requests

**Solution:**
- Reduce batch size in populate scripts
- Add delays between batches
- Use lower tier OpenAI account

### Issue: Slow Vector Search

**Cause:** Missing or outdated IVFFLAT index

**Solution:**
```sql
-- Rebuild index
DROP INDEX IF EXISTS idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding 
ON chunks USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Analyze table
ANALYZE chunks;
```

### Issue: CORS Errors in Browser

**Cause:** Frontend trying to access API from different origin

**Solution:** Already configured in `backend/main.py` with `allow_origins=["*"]`

### Issue: No Results Returned

**Causes:**
1. No embeddings populated
2. Threshold too high
3. No matching properties

**Solutions:**
```powershell
# 1. Check embedding coverage
curl http://localhost:8787/api/stats

# 2. Lower threshold
curl "http://localhost:8787/api/search?q=apartment&threshold=0.5"

# 3. Try broader query
curl "http://localhost:8787/api/search?q=apartment"
```

## 📐 Architecture

```
┌─────────────┐
│   Browser   │
│   (React)   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────┐
│   FastAPI Server        │
│   (Port 8787)           │
│                         │
│  ┌──────────────────┐   │
│  │ /api/search      │   │
│  │ /api/properties  │   │
│  │ /api/stats       │   │
│  └──────────────────┘   │
└───┬─────────────┬───────┘
    │             │
    │ OpenAI     │ Supabase
    │ Embeddings │ REST API
    ▼             ▼
┌─────────────┐ ┌──────────────┐
│  OpenAI API │ │  Supabase    │
│ (text-emb-  │ │              │
│  3-small)   │ │  ┌────────┐  │
└─────────────┘ │  │chunks  │  │
                │  │table   │  │
                │  └────────┘  │
                │  ┌────────┐  │
                │  │proper- │  │
                │  │ties    │  │
                │  └────────┘  │
                │  ┌────────┐  │
                │  │trans-  │  │
                │  │actions │  │
                │  └────────┘  │
                └──────────────┘
```

## 🎨 Frontend

Simple HTML/CSS/JS interface at `frontend/`:

- `index.html`: Search UI structure
- `style.css`: Responsive design (TO BE CREATED)
- `script.js`: Search logic and API calls (TO BE CREATED)

Served at http://localhost:8787/

## 🔒 Security & Rate Limiting

**Implemented:**
- ✅ Service role key kept server-side only
- ✅ CORS configured for dev (allow all origins)
- ✅ SlowAPI rate limiting per IP
- ✅ Input validation (query length, parameter ranges)
- ✅ HTTP timeouts (30s for Supabase, retries for OpenAI)

**Rate Limits:**
- `/api/search`: 30 req/min
- `/api/properties`: 60 req/min
- `/api/stats`: 30 req/min

## 📊 Cost Estimation

**OpenAI Embedding Costs:**
- Model: text-embedding-3-small
- Price: ~$0.00002 per 1K tokens
- Average property description: ~50 tokens
- **Cost for 10,000 properties**: ~$0.01 USD

**Supabase:**
- Free tier: 500 MB database, 2 GB bandwidth
- Paid tier: $25/mo for 8 GB database

## 🚀 Next Steps

### Immediate (Complete Implementation)

1. ✅ Create `frontend/style.css` with responsive design
2. ✅ Create `frontend/script.js` with search logic
3. ✅ Create `backend/scripts/populate_chunks.py`
4. ✅ Create `backend/scripts/test_queries.py`
5. ✅ Run migrations in Supabase
6. ✅ Populate embeddings
7. ✅ Test all endpoints

### Future Enhancements

- **CSV Export**: `/api/export` endpoint
- **Analytics**: `/api/insights` for market trends
- **Authentication**: Supabase Auth integration
- **Caching**: Redis layer for repeated queries
- **Advanced Filters**: Price per sqft, amenities, floor level
- **Property Recommendations**: "Properties like this"
- **Alert System**: Save searches, get notifications

## 📝 Notes

- **Embeddings are cached**: No regeneration unless content changes
- **Chunks vs Properties**: Chunks recommended for flexibility
- **IVFFLAT Index**: Optimal for 100K-1M vectors with lists=100
- **Similarity Threshold**: 0.70-0.75 works well for most queries
- **Phone Numbers**: Stored as digits only in transactions

## 📄 License

Private project - All rights reserved

## 🤝 Support

For issues:
1. Check this README troubleshooting section
2. Review API docs at `/api/docs`
3. Check server logs for errors
4. Verify Supabase connection with `/health` endpoint
