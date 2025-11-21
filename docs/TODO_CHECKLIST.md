# Action Items Checklist

## ✅ COMPLETED (Auto-fixed by AI)

- [x] Remove hardcoded password from `apply_rpc_functions.py`
- [x] Add `SUPABASE_DB_URL` environment variable support
- [x] Implement pagination in all fetch methods
- [x] Add retry logic with exponential backoff
- [x] Fix date filter overwriting issue
- [x] Create `phone_utils.py` with E.164 normalization
- [x] Update `owner_portfolio()` to use normalized phones
- [x] Add data quality filters (size_sqft >= 300, price > 0)
- [x] Fix Period object serialization in analytics
- [x] Improve correlation with NaN handling
- [x] Fix `likely_sellers()` null date handling
- [x] Add timezone-aware date calculations
- [x] Test phone normalization utility ✅

---

## 🔧 MANUAL TASKS REQUIRED

### IMMEDIATE (Before Running System)

- [ ] **Set Environment Variables**
  ```powershell
  $env:SUPABASE_DB_URL = "postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres?sslmode=require"
  $env:SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
  $env:SUPABASE_SERVICE_ROLE_KEY = "YOUR_SERVICE_ROLE_KEY"
  ```

- [ ] **Test the fixes**
  ```bash
  python .\test_rpc_functions.py
  python .\analytics_engine.py
  ```

### HIGH PRIORITY (This Week)

- [ ] **Update Documentation**
  - [ ] Search `README.md` for `DubaiRealEstateAnalytics` and replace with `AnalyticsEngine`
  - [ ] Search `QUICK_REFERENCE.md` for class name references
  - [ ] Verify all import examples match actual code

- [ ] **Update Ingestion Scripts**
  - [ ] Import `from phone_utils import normalize_phone`
  - [ ] Apply normalization to all phone fields before insert
  - [ ] Update existing records: `UPDATE owners SET norm_phone = normalize_phone(raw_phone)`

### MEDIUM PRIORITY (This Month)

- [ ] **Find and Update CMA Generator**
  - [ ] Search for CMA/report generation script
  - [ ] Add status code validation
  - [ ] Add explicit key mapping with fallbacks
  - [ ] Save `report_meta.json` alongside PDFs

- [ ] **Orchestrator File**
  - [ ] Identify main orchestration script
  - [ ] Implement intent routing:
    - `ownership_lookup` → `v_current_owner`
    - `transaction_history` → `v_transaction_history`
  - [ ] Update documentation to reference correct file name

### LOW PRIORITY (When Convenient)

- [ ] **Fix Count Tool**
  - [ ] Find `count_excel_rows.py` or similar
  - [ ] Fix path glob: `glob.glob('./.data_raw/*.xlsx')`
  - [ ] Add live Supabase count query
  - [ ] Report discrepancy

- [ ] **Database Optimization**
  - [ ] Run ANALYZE on all tables
  - [ ] Consider indexes on: `community`, `transaction_date`, `norm_phone`
  - [ ] Test query performance with pagination

---

## 📋 VERIFICATION STEPS

After completing manual tasks, verify:

1. **Security Check**
   ```bash
   # Ensure no passwords in any file
   grep -r "password" *.py
   # Should only find env variable references
   ```

2. **Pagination Test**
   ```python
   # In Python console
   from analytics_engine import AnalyticsEngine
   engine = AnalyticsEngine()
   df = engine.fetch_transactions()
   print(f"Fetched {len(df)} transactions")
   # Should see > 1000 if you have that many
   ```

3. **Phone Normalization Test**
   ```python
   from phone_utils import normalize_phone
   print(normalize_phone("0501234567"))  # Should print: +971501234567
   ```

4. **Analytics Quality Test**
   ```python
   from analytics_engine import AnalyticsEngine
   engine = AnalyticsEngine()
   stats = engine.market_stats("Business Bay")
   print(stats)  # Should show realistic numbers with size filter applied
   ```

---

## 🚨 CRITICAL REMINDERS

1. **NEVER** commit `.env` files or files containing `SUPABASE_DB_URL`
2. **ALWAYS** use environment variables for credentials
3. **TEST** pagination with large datasets before production
4. **VALIDATE** phone normalization doesn't break existing lookups
5. **BACKUP** database before running batch updates

---

## 📞 PHONE NORMALIZATION MIGRATION

If you have existing data, run this migration:

```sql
-- Add norm_phone column if not exists
ALTER TABLE owners ADD COLUMN IF NOT EXISTS norm_phone TEXT;

-- Update using PostgreSQL regex (adjust for your data)
UPDATE owners 
SET norm_phone = 
  CASE 
    WHEN raw_phone ~ '^\\+971[0-9]{9}$' THEN raw_phone
    WHEN raw_phone ~ '^971[0-9]{9}$' THEN '+' || raw_phone
    WHEN raw_phone ~ '^0[0-9]{9}$' THEN '+971' || substring(raw_phone from 2)
    WHEN raw_phone ~ '^[0-9]{9}$' THEN '+971' || raw_phone
    ELSE NULL
  END
WHERE norm_phone IS NULL;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_owners_norm_phone ON owners(norm_phone);
```

---

## 🎯 SUCCESS CRITERIA

System is ready when:

- ✅ All tests pass without errors
- ✅ No hardcoded credentials in code
- ✅ Pagination fetches all records correctly
- ✅ Phone lookups work with multiple formats
- ✅ Analytics exclude noise data (< 300 sqft)
- ✅ Documentation matches actual class names
- ✅ Environment variables properly set

---

*Last updated: 2025-11-11*
