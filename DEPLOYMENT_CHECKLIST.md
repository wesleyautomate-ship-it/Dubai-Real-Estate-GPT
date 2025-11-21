# 🚀 Deployment Checklist - Dubai Real Estate Semantic Search

## ✅ Step 1: Environment Configuration

Before running the server, you MUST configure your `.env` file with actual values:

### Required Environment Variables

```powershell
# Open .env and update these values:
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_actual_service_role_key_here
OPENAI_API_KEY=sk-your_actual_openai_key_here
API_PORT=8787
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIM=1536
```

**Where to find these:**
- **SUPABASE_URL & KEY**: Supabase project settings → API
- **OPENAI_API_KEY**: OpenAI account → API keys

### Update .env File

```powershell
# PowerShell command to verify current values:
Get-Content .env | Select-String "SUPABASE_URL|OPENAI_API_KEY|API_PORT"
```

---

## ✅ Step 2: Database Migrations

**Status**: ⏳ PENDING - Must run in Supabase

Go to **Supabase SQL Editor** and run these files in order:

```sql
-- File 1: Create chunks table
-- Copy entire contents of: database/migrations/create_chunks_table.sql
-- Paste and run in Supabase

-- File 2: Add property embeddings columns
-- Copy entire contents of: database/migrations/add_property_embeddings.sql
-- Paste and run in Supabase

-- File 3: Create RPC functions
-- Copy entire contents of: sql/create_rpc.sql
-- Paste and run in Supabase

-- File 4: Analyze tables for optimal performance
ANALYZE chunks;
ANALYZE properties;
```

**Verification in Supabase:**
```sql
-- Check chunks table
SELECT table_name FROM information_schema.tables WHERE table_name = 'chunks';

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename IN ('chunks', 'properties') 
AND indexname LIKE '%embedding%';

-- Check RPC functions
SELECT routine_name FROM information_schema.routines 
WHERE routine_name LIKE 'semantic%' OR routine_name = 'db_stats';
```

---

## ✅ Step 3: Python Dependencies

**Status**: ✅ COMPLETED

```powershell
# Virtual environment created: .\venv
# Dependencies installed successfully:
# - FastAPI 0.121.1
# - Uvicorn 0.38.0
# - OpenAI 2.7.2
# - httpx 0.28.1
# - python-dotenv 1.2.1
# - All other requirements
```

---

## ✅ Step 4: Populate Embeddings

**Status**: ⏳ PENDING - Requires updated .env

### Option A: Populate Chunks Table (Recommended)

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Run population script
python backend/scripts/populate_chunks.py
```

**Expected output:**
```
======================================================================
🤖 Populating Chunks Table with Property Embeddings
======================================================================

📊 Fetching properties from Supabase...
   Found X properties

📝 Generating descriptions...
[####################################] 100%

🔄 Generating embeddings (OpenAI)...
[####################################] 100%

📦 Preparing chunks for insertion...
[####################################] 100%

💾 Inserting chunks into database...
[####################################] 100%

======================================================================
✅ Chunks Population Complete!
======================================================================
```

### Option B: Populate Properties Embeddings (Alternative)

```powershell
python backend/scripts/populate_property_embeddings.py
```

**Time estimate**: 5-30 minutes depending on property count and OpenAI rate limits

---

## ✅ Step 5: Start the Server

**Status**: ⏳ PENDING - Requires .env & migrations

```powershell
# Activate venv (if not already active)
.\venv\Scripts\Activate.ps1

# Start server
python run_server.py
```

**Expected output:**
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
✅ Database connected - X properties
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8787
```

**Server will run indefinitely** - press `Ctrl+C` to stop

---

## ✅ Step 6: Test the Application

### Browser Testing

```
1. Open: http://localhost:8787
2. Type: "3 bedroom apartment in Dubai Marina"
3. Press Enter
4. Verify results appear with property cards
```

### API Testing

```powershell
# In new PowerShell window (keep server running):

# Test search endpoint
Invoke-WebRequest -Uri "http://localhost:8787/api/search?q=apartment" -Method GET

# Test stats endpoint
Invoke-WebRequest -Uri "http://localhost:8787/api/stats" -Method GET

# Test health check
Invoke-WebRequest -Uri "http://localhost:8787/health" -Method GET

# View API documentation
Start-Process "http://localhost:8787/api/docs"
```

### Automated Tests

```powershell
# Run test suite (while server is running)
.\venv\Scripts\Activate.ps1
python backend/scripts/test_queries.py
```

---

## ⚠️ Troubleshooting

### Issue: "SUPABASE_URL not set in environment"

**Solution**: Update `.env` with actual values
```powershell
# Edit .env file and replace placeholder values:
# SUPABASE_URL=https://YOUR_PROJECT.supabase.co  <- Replace with your URL
# SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...          <- Replace with your key
# OPENAI_API_KEY=sk-proj-...                    <- Replace with your key
```

### Issue: Port 8787 already in use

**Solution**: 
```powershell
# Option 1: Find and kill process
$process = Get-NetTCPConnection -LocalPort 8787 -ErrorAction SilentlyContinue
if ($process) { Stop-Process -Id $process.OwningProcess -Force }

# Option 2: Change port in .env
# API_PORT=8788
```

### Issue: "No embeddings found" or no search results

**Solutions**:
1. Run `python backend/scripts/populate_chunks.py`
2. Check IVFFLAT index was created: 
   ```sql
   SELECT * FROM pg_indexes WHERE indexname LIKE '%embedding%';
   ```
3. Verify embeddings exist:
   ```sql
   SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;
   ```

### Issue: "401 Unauthorized" from Supabase

**Solution**: Verify you're using the **service_role** key (not anon key)
```powershell
# Check current key in .env
Select-String -Path ".env" -Pattern "SUPABASE_SERVICE_ROLE_KEY"
```

### Issue: OpenAI rate limit errors

**Solution**: 
```powershell
# Reduce batch size in populate script
# Edit backend/scripts/populate_chunks.py line 81:
# all_embeddings = await embed_batch(descriptions, batch_size=25)  # Reduce from 50
```

---

## 📋 Deployment Verification Checklist

- [ ] **Step 1**: `.env` file has real Supabase and OpenAI credentials
- [ ] **Step 2**: All SQL migrations run successfully in Supabase
- [ ] **Step 3**: Python venv created and dependencies installed
- [ ] **Step 4**: Chunks/property embeddings populated (at least partially)
- [ ] **Step 5**: Server starts without errors on port 8787
- [ ] **Step 6**: Frontend loads at http://localhost:8787
- [ ] **Step 6**: Search returns results for "apartment"
- [ ] **Step 6**: API docs available at http://localhost:8787/api/docs

---

## 🎯 Quick Start Commands

```powershell
# 1. Configure .env with real credentials
# (Use your editor or PowerShell to update .env)

# 2. Run database migrations (in Supabase SQL Editor)
# Copy/paste files from: database/migrations/ and sql/create_rpc.sql

# 3. Activate venv and populate embeddings
.\venv\Scripts\Activate.ps1
python backend/scripts/populate_chunks.py

# 4. Start server (in same PowerShell window)
python run_server.py

# 5. Test in browser
Start-Process "http://localhost:8787"

# 6. Test API (in new PowerShell window)
.\venv\Scripts\Activate.ps1
python backend/scripts/test_queries.py
```

---

## 📊 Current Status

| Component | Status | Details |
|-----------|--------|---------|
| Python 3.14 | ✅ Available | Ready to use |
| Virtual Environment | ✅ Created | `./venv` |
| Dependencies | ✅ Installed | 23 packages |
| Database Config | ⏳ Pending | Needs `.env` update |
| DB Migrations | ⏳ Pending | Run in Supabase |
| Embeddings | ⏳ Pending | Run after migrations |
| Server | ⏳ Ready | `python run_server.py` |
| Frontend | ✅ Ready | All 3 files created |
| API Endpoints | ✅ Ready | All 3 endpoints defined |

---

## 📞 Need Help?

See these files for detailed information:

- **Complete Guide**: `README_SEARCH.md`
- **Architecture**: `IMPLEMENTATION_COMPLETE.md`
- **Troubleshooting**: `README_SEARCH.md#troubleshooting`
- **API Docs**: Visit http://localhost:8787/api/docs after server starts

---

**Next Action**: Update `.env` file with your actual Supabase and OpenAI credentials, then follow steps 2-6 above.
