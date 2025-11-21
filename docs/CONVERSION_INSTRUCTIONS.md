# Square Meter to Square Feet Conversion Instructions

## Problem Identified

The database columns are named `size_sqft` but they actually contain **square meters** (sqm), not square feet (sqft).

This causes:
- Price per sqft calculations to actually be **price per sqm**
- Incorrect size comparisons
- Misleading analytics

## Conversion Factor

**1 square meter = 10.764 square feet**

## Current Values (Before Conversion)

Based on test results:
- Business Bay avg "PSF": AED 14,732 (actually per sqm)
- Dubai Marina avg "PSF": AED 22,169 (actually per sqm)
- Palm Jumeirah avg "PSF": AED 51,606 (actually per sqm)

## After Conversion (Expected Values)

After multiplying sizes by 10.764:
- Business Bay avg PSF: ~AED **1,369** (14,732 ÷ 10.764)
- Dubai Marina avg PSF: ~AED **2,060** (22,169 ÷ 10.764)
- Palm Jumeirah avg PSF: ~AED **4,794** (51,606 ÷ 10.764)

These are more realistic Dubai price per sqft values!

---

## Step-by-Step Conversion Process

### Step 1: Backup Your Database ⚠️

**CRITICAL**: Before running any updates, create a backup!

In Supabase Dashboard:
1. Go to Settings → Database
2. Create a backup or export tables

### Step 2: Run the Conversion SQL

Run `convert_sqm_to_sqft.sql` in Supabase SQL Editor:

```sql
-- This will update all records
UPDATE transactions 
SET size_sqft = size_sqft * 10.764
WHERE size_sqft IS NOT NULL AND size_sqft > 0;

UPDATE properties 
SET size_sqft = size_sqft * 10.764
WHERE size_sqft IS NOT NULL AND size_sqft > 0;
```

### Step 3: Update Data Quality Filters

After conversion, the size filter needs adjustment:

**Current filter** (thinking it's sqm):
```python
df = df[df['size_sqft'] >= 300]  # This was 300 sqm = 3,229 sqft
```

**New filter options**:

**Option A - Keep similar logic (100 sqm minimum):**
```python
df = df[df['size_sqft'] >= 1076]  # 100 sqm = 1,076 sqft
```

**Option B - Realistic Dubai minimum (50 sqm):**
```python
df = df[df['size_sqft'] >= 538]  # 50 sqm = 538 sqft
```

**Option C - Very conservative (300 sqft actual):**
```python
df = df[df['size_sqft'] >= 300]  # Actual 300 sqft
```

### Step 4: Update Analytics Engine

The filter appears in multiple places in `analytics_engine.py`:

**Line 186:**
```python
df = df[df['size_sqft'] >= 1076]  # Changed: 100 sqm minimum
```

**Line 217:**
```python
df = df[df['size_sqft'] >= 1076]  # Changed: 100 sqm minimum
```

**Line 430:**
```python
df = df[df['size_sqft'] >= 1076]  # Changed: 100 sqm minimum
```

### Step 5: Verify the Conversion

Run verification query in Supabase:

```sql
SELECT 
    community,
    COUNT(*) as transactions,
    ROUND(AVG(price / size_sqft), 2) as avg_price_per_sqft,
    ROUND(AVG(size_sqft), 2) as avg_size_sqft
FROM transactions
WHERE size_sqft IS NOT NULL AND price > 0
GROUP BY community
ORDER BY transactions DESC
LIMIT 10;
```

Expected results:
- Average sizes: 1,000-3,000 sqft (reasonable for Dubai apartments/villas)
- Price per sqft: AED 1,000-5,000 (realistic Dubai market rates)

### Step 6: Test Your Application

Run tests after conversion:

```bash
python .\test_rpc_functions.py
python .\test_analytics.py
python .\test_rpc_multiple_communities.py
```

---

## Quick Command Sequence

```powershell
# 1. Backup database (do this in Supabase dashboard)

# 2. Run conversion SQL in Supabase SQL Editor
# Copy contents of convert_sqm_to_sqft.sql and execute

# 3. Update analytics_engine.py filters
# Change all instances of >= 300 to >= 1076

# 4. Test
python .\test_rpc_functions.py
python .\test_analytics.py
```

---

## Rollback (If Needed)

If something goes wrong, you can reverse the conversion:

```sql
UPDATE transactions 
SET size_sqft = size_sqft / 10.764
WHERE size_sqft IS NOT NULL AND size_sqft > 0;

UPDATE properties 
SET size_sqft = size_sqft / 10.764
WHERE size_sqft IS NOT NULL AND size_sqft > 0;
```

---

## Summary of Changes

| Item | Before (sqm) | After (sqft) |
|------|-------------|--------------|
| **Column Data** | Square meters | Square feet (×10.764) |
| **Size Filter** | >= 300 | >= 1076 (100 sqm) |
| **Business Bay Avg PSF** | AED 14,732 (wrong) | AED 1,369 (correct) |
| **Dubai Marina Avg PSF** | AED 22,169 (wrong) | AED 2,060 (correct) |
| **Palm Jumeirah Avg PSF** | AED 51,606 (wrong) | AED 4,794 (correct) |

---

## Important Notes

1. ⚠️ **This is a one-time conversion** - Do NOT run twice!
2. ✅ After conversion, all calculations will be in actual square feet
3. ✅ Price per sqft values will match Dubai market reality
4. ✅ All future ingestions should convert sqm to sqft at ingestion time
5. 📊 Update any reports/dashboards that reference these values

---

*Conversion factor: 1 sqm = 10.764 sqft*
