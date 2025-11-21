-- ============================================================
-- CONVERT SQUARE METERS TO SQUARE FEET
-- ============================================================
-- Issue: Database columns named size_sqft actually contain square meters
-- Solution: Convert all size values from sqm to sqft (multiply by 10.764)
-- 1 square meter = 10.764 square feet

-- ============================================================
-- 1. UPDATE TRANSACTIONS TABLE
-- ============================================================
UPDATE transactions 
SET size_sqft = size_sqft * 10.764
WHERE size_sqft IS NOT NULL
  AND size_sqft > 0;

-- ============================================================
-- 2. UPDATE PROPERTIES TABLE
-- ============================================================
UPDATE properties 
SET size_sqft = size_sqft * 10.764
WHERE size_sqft IS NOT NULL
  AND size_sqft > 0;

-- ============================================================
-- 3. VERIFICATION QUERY
-- ============================================================
-- Check some sample conversions
SELECT 
    community,
    building,
    unit,
    size_sqft,
    ROUND(size_sqft / 10.764, 2) as original_sqm,
    price,
    ROUND(price / size_sqft, 2) as price_per_sqft
FROM transactions
WHERE size_sqft IS NOT NULL
LIMIT 10;

-- ============================================================
-- 4. STATISTICS AFTER CONVERSION
-- ============================================================
SELECT 
    'transactions' as table_name,
    COUNT(*) as total_rows,
    COUNT(size_sqft) as rows_with_size,
    ROUND(AVG(size_sqft), 2) as avg_size_sqft,
    ROUND(MIN(size_sqft), 2) as min_size_sqft,
    ROUND(MAX(size_sqft), 2) as max_size_sqft
FROM transactions
UNION ALL
SELECT 
    'properties' as table_name,
    COUNT(*) as total_rows,
    COUNT(size_sqft) as rows_with_size,
    ROUND(AVG(size_sqft), 2) as avg_size_sqft,
    ROUND(MIN(size_sqft), 2) as min_size_sqft,
    ROUND(MAX(size_sqft), 2) as max_size_sqft
FROM properties;

-- ============================================================
-- NOTES:
-- ============================================================
-- After running this conversion:
-- - All size_sqft columns will contain actual square feet
-- - All price per sqft calculations will be correct
-- - You MUST update the data quality filter in analytics_engine.py:
--   Change: size_sqft >= 300  (which was really 300 sqm = 3,229 sqft)
--   To: size_sqft >= 3229  (minimum realistic size in sqft)
--   Or: size_sqft >= 1076  (100 sqm minimum, more reasonable)
-- ============================================================
