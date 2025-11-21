# Dubai Real Estate Database

Complete end-to-end system for ingesting and querying Dubai real estate transactions from Excel files into a Supabase PostgreSQL database.

## Overview

This system:
- **Processes 40+ Excel files** (~185MB) containing Dubai real estate transactions
- **Merges buyer/seller rows** into unified transaction records
- **Performs fuzzy alias matching** for community and building names
- **Uploads to Supabase** with normalized phone numbers and dates
- **Provides views** for current ownership and transaction history

## Quick Start

### Step 1: Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com) and sign up/login
2. Click **"New project"**
3. Set project details:
   - Name: `dubai-real-estate`
   - Database Password: Choose a strong password
   - Region: Select closest to you
4. Wait ~2 minutes for provisioning
5. Get your credentials:
   - Go to **Settings -> API**
   - Copy **Project URL** (format: `https://xxxxx.supabase.co`)
   - Copy **service_role key** (scroll down - NOT the anon key)

### Step 2: Apply Database Schema

1. In Supabase dashboard, open **SQL Editor**
2. Copy and run the entire `supabase_schema.sql` file
3. Verify tables created: `transactions`, `owners`, `properties`, `aliases`

### Step 3: Set Environment Variables

Run the setup script in PowerShell:

```powershell
.\set_supabase_env.ps1
```

Or set manually:

```powershell
$env:SUPABASE_URL = "https://xxxxx.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "eyJhbGc..."
```

To persist permanently (optional):

```powershell
[Environment]::SetEnvironmentVariable("SUPABASE_URL","https://xxxxx.supabase.co","User")
[Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY","YOUR_KEY","User")
```

### Step 4: Run Ingestion

```powershell
python ingest_dubai_real_estate.py
```

Expected output:
```
Loading aliases...
Reading files...
Greens Jan 2025.xlsx -> 256 transactions
Business Bay Jan 2025.xlsx -> 8652 transactions
...
Built 45000 transaction rows from 40 files.
Uploaded 1000 of 45000
Uploaded 2000 of 45000
...
Done.
```

### Step 5: Validate Data

In Supabase SQL Editor:

```sql
-- Count total transactions
SELECT count(*) FROM transactions;

-- View recent transactions
SELECT community, building, unit, buyer_name, seller_name, price, transaction_date
FROM transactions
ORDER BY transaction_date DESC
LIMIT 10;

-- Check current owners
SELECT * FROM v_current_owner
WHERE community = 'Business Bay'
LIMIT 10;

-- Review fuzzy alias suggestions
SELECT * FROM aliases WHERE confidence < 0.9;
```

### Step 6: Run the React Frontend

The `frontend/` directory now contains a Vite + React application that talks to the FastAPI backend.

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` calls to `http://localhost:8787`, so be sure the backend is running. Visit the printed URL (usually http://localhost:5173) to use the new UI.

## Project Structure

```
Dubai Real Estate Database/
|-- .data_raw/                           # Excel files (40 files, ~185MB)
|   |-- Business Bay Jan 2025.xlsx
|   |-- Dubai Marina Jan 2025.xlsx
|   -- ...
|-- ingest_dubai_real_estate.py         # Main ingestion script
|-- supabase_schema.sql                 # Database schema
|-- set_supabase_env.ps1                # Environment setup helper
-- README.md                           # This file
```

## Database Schema

### Tables

**transactions** - Raw transaction records
- `community`, `building`, `unit` - Property identifiers
- `seller_name`, `seller_phone` - Seller info (ampersand-delimited for multiple)
- `buyer_name`, `buyer_phone` - Buyer info
- `price`, `currency`, `transaction_date` - Deal details
- `property_type`, `size_sqft` - Property attributes
- `source_file`, `metadata` - Provenance tracking

**owners** - Unique owner registry (future use)

**properties** - Normalized property registry (future use)

**aliases** - Fuzzy name resolution
- Stores community and building name variations
- Auto-generated during ingestion with confidence scores

### Views

**v_current_owner** - Latest owner per property
```sql
SELECT * FROM v_current_owner
WHERE building = 'AL GHOZLAN 3' AND unit = '315';
```

**v_transaction_history** - All deals by property
```sql
SELECT * FROM v_transaction_history
WHERE community = 'Greens'
ORDER BY transaction_date DESC;
```

## Data Format

### Input Excel Files

Each Excel file contains rows with buyer/seller entries:

| Regis | ProcedureValue | BuildingNameEn | UnitNumber | ProcedurePartyTypeNameEn | NameEn | Mobile |
|-------|----------------|----------------|------------|--------------------------|--------|---------|
| 2024-03-20 | 938000 | AL GHOZLAN 3 | 315 | Seller | MOHAMMED ABDULLAH | 971-55-5734830 |
| 2024-03-20 | 938000 | AL GHOZLAN 3 | 315 | Buyer | HIBA MAZAHIR SHEIKH | 971-55-4280400 |

### Script Processing

1. **Normalizes columns** - Handles variations in header names
2. **Groups consecutive rows** - Pairs buyers/sellers by date, building, unit, price
3. **Merges parties** - Multiple buyers/sellers joined with `&`
4. **Resolves aliases** - Fuzzy matches "Dubai Marina" ~ "Dubai Marin" ~ "Dubai Marina"
5. **Extracts community** - From data columns or filename
6. **Cleans phones** - Strips to digits only

### Output Transaction Record

```json
{
  "community": "Greens",
  "building": "AL GHOZLAN 3",
  "unit": "315",
  "property_type": "Unit",
  "size_sqft": 70.02,
  "seller_name": "MOHAMMED ABDULLAH J ABOLFARAJ",
  "seller_phone": "971555734830",
  "buyer_name": "HIBA MAZAHIR SHEIKH",
  "buyer_phone": "971554280400",
  "transaction_date": "2024-03-20",
  "price": 938000,
  "currency": "AED",
  "source_file": "Greens Jan 2025.xlsx"
}
```

## Troubleshooting

### Issue: Missing environment variables

```
SystemExit: Missing environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

**Solution:** Run `.\set_supabase_env.ps1` or set manually in PowerShell

### Issue: 401 Unauthorized

```
Upload error batch 0-1000: 401 {"message":"Invalid API key"}
```

**Solution:** 
- Verify you copied the **service_role** key, not anon key
- Check SUPABASE_URL matches your project

### Issue: 400 Bad Request

```
Upload error batch 0-1000: 400 {"message":"invalid input syntax for type numeric"}
```

**Solution:** Data type mismatch - check the specific file and column causing issues

### Issue: Payload too large

```
Upload error batch 0-1000: 413 Payload Too Large
```

**Solution:** Reduce BATCH size in script from 1000 to 300

### Issue: No files found

```
No Excel or CSV files found in .data_raw.
```

**Solution:** Ensure files are in `.data_raw/` directory (note the dot prefix)

## Configuration

### Fuzzy Matching Threshold

Edit `ingest_dubai_real_estate.py`:

```python
# Line 143
fuzzy_threshold: int = 90  # Lower = more matches, higher = more strict
```

### Batch Upload Size

```python
# Line 357
BATCH = 1000  # Reduce if getting payload errors
```

### Community Name Extraction

```python
# Line 211 - Add more column names if needed
community_raw = get_col_value(row, canon_map, [
    "Master Project Land", "Master Project", "Project Lnd", 
    "Project", "Community", "Area"
])
```

### Switching LLM Providers (OpenAI vs Gemini)

The chat agent can now run on either OpenAI or Gemini. OpenAI remains the default (and is still required for embeddings and ingestion), but you can switch conversational responses to Gemini by updating your `.env`:

```env
LLM_PROVIDER=gemini           # or "openai"
OPENAI_CHAT_MODEL=gpt-4o-mini
GEMINI_API_KEY=your-gemini-key
GEMINI_CHAT_MODEL=gemini-1.5-flash
```

Gemini support currently handles text responses only (tool-calling features are available when `LLM_PROVIDER=openai`). After changing providers, restart the FastAPI server.

## Example Queries

### Find properties by owner phone
```sql
SELECT * FROM v_current_owner
WHERE owner_phone LIKE '%555734830%';
```

### Price trends by community
```sql
SELECT 
  community,
  DATE_TRUNC('month', transaction_date) as month,
  AVG(price) as avg_price,
  COUNT(*) as sales_count
FROM transactions
WHERE transaction_date >= '2024-01-01'
GROUP BY community, month
ORDER BY month DESC, avg_price DESC;
```

### Building inventory
```sql
SELECT 
  community,
  building,
  COUNT(DISTINCT unit) as total_units,
  COUNT(DISTINCT CASE WHEN buyer_name IS NOT NULL THEN unit END) as sold_units
FROM transactions
GROUP BY community, building
ORDER BY total_units DESC;
```

### Recent high-value sales
```sql
SELECT 
  community, building, unit, price,
  buyer_name, transaction_date
FROM transactions
WHERE price > 5000000
ORDER BY transaction_date DESC, price DESC
LIMIT 20;
```

## Next Enhancements

1. **Unique constraints** - Prevent duplicate transaction uploads
2. **Owner clustering** - Link name variations to same person
3. **Property normalization** - Populate `properties` table from transactions
4. **Scheduled ingestion** - Auto-process new monthly files
5. **Alias curation** - Review and promote high-confidence aliases
6. **Web dashboard** - Query interface for non-technical users

## Notes

- **service_role key** gives full database access - keep it private!
- First run will generate many alias suggestions (confidence=0.5)
- Review aliases table and update canonical names for consistency
- Phone numbers are stored as digit-only strings
- Multiple buyers/sellers are ampersand-delimited
- Metadata field stores row grouping info for debugging

## License

Private project - All rights reserved

## Support

For issues or questions, review the Troubleshooting section above or check Supabase documentation at https://supabase.com/docs
