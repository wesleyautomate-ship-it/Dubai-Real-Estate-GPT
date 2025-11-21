-- ============================================================
-- PRE-CONVERSION CHECK
-- Run this BEFORE conversion to see current values
-- ============================================================

SELECT 
    'BEFORE CONVERSION - Current values (in square meters)' as status;

SELECT 
    community,
    COUNT(*) as transactions,
    ROUND(AVG(size_sqft), 2) as avg_size_sqm,  -- Actually sqm, not sqft!
    ROUND(AVG(price / size_sqft), 2) as price_per_sqm,  -- Actually per sqm!
    ROUND(MIN(size_sqft), 2) as min_size,
    ROUND(MAX(size_sqft), 2) as max_size
FROM transactions
WHERE size_sqft IS NOT NULL AND price > 0 AND size_sqft > 0
GROUP BY community
ORDER BY transactions DESC
LIMIT 5;

-- Expected results BEFORE conversion:
-- Business Bay: avg ~160 sqm, price_per_sqm ~14,732
-- Dubai Marina: avg ~140 sqm, price_per_sqm ~22,169
-- Palm Jumeirah: avg ~500 sqm, price_per_sqm ~51,606
