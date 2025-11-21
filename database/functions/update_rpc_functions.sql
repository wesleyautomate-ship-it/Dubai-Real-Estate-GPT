-- ============================================================
-- DROP EXISTING FUNCTIONS BEFORE UPDATING
-- ============================================================

DROP FUNCTION IF EXISTS market_stats(text,text,integer,date,date);
DROP FUNCTION IF EXISTS find_comparables(text,text,integer,numeric,integer,integer);
DROP FUNCTION IF EXISTS search_owners(text,integer);

-- ============================================================
-- RECREATE FUNCTIONS WITH CORRECT TYPES
-- ============================================================

-- ============================================================
-- 1. MARKET STATISTICS (Fixed: DOUBLE PRECISION instead of NUMERIC)
-- ============================================================
CREATE OR REPLACE FUNCTION market_stats(
    p_community TEXT DEFAULT NULL,
    p_property_type TEXT DEFAULT NULL,
    p_bedrooms INTEGER DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    avg_price DOUBLE PRECISION,
    median_price DOUBLE PRECISION,
    min_price DOUBLE PRECISION,
    max_price DOUBLE PRECISION,
    total_transactions BIGINT,
    total_volume DOUBLE PRECISION,
    avg_price_per_sqft DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ROUND(AVG(price), 2) as avg_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price,
        MIN(price) as min_price,
        MAX(price) as max_price,
        COUNT(*)::BIGINT as total_transactions,
        SUM(price) as total_volume,
        ROUND(AVG(price / NULLIF(size_sqft, 0)), 2) as avg_price_per_sqft
    FROM transactions
    WHERE (p_community IS NULL OR community ILIKE '%' || p_community || '%')
      AND (p_property_type IS NULL OR property_type ILIKE '%' || p_property_type || '%')
      AND (p_bedrooms IS NULL OR bedrooms = p_bedrooms)
      AND (p_start_date IS NULL OR transaction_date >= p_start_date)
      AND (p_end_date IS NULL OR transaction_date <= p_end_date)
      AND price > 0;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 2. FIND COMPARABLE PROPERTIES (Fixed: BIGINT for bedrooms, DOUBLE PRECISION)
-- ============================================================
CREATE OR REPLACE FUNCTION find_comparables(
    p_community TEXT,
    p_property_type TEXT DEFAULT NULL,
    p_bedrooms INTEGER DEFAULT NULL,
    p_size_sqft NUMERIC DEFAULT NULL,
    p_months_back INTEGER DEFAULT 12,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    community TEXT,
    building TEXT,
    unit TEXT,
    property_type TEXT,
    bedrooms BIGINT,
    size_sqft DOUBLE PRECISION,
    price DOUBLE PRECISION,
    price_per_sqft DOUBLE PRECISION,
    transaction_date DATE,
    buyer_name TEXT,
    similarity_score DOUBLE PRECISION
) AS $$
DECLARE
    v_cutoff_date DATE := CURRENT_DATE - (p_months_back || ' months')::INTERVAL;
BEGIN
    RETURN QUERY
    SELECT 
        t.community,
        t.building,
        t.unit,
        t.property_type,
        t.bedrooms,
        t.size_sqft,
        t.price,
        ROUND(t.price / NULLIF(t.size_sqft, 0), 2) as price_per_sqft,
        t.transaction_date,
        t.buyer_name,
        -- Simple similarity: prioritize exact bedroom match, then size proximity
        CASE 
            WHEN t.bedrooms = p_bedrooms THEN 100.0
            WHEN p_bedrooms IS NULL THEN 80.0
            ELSE 50.0
        END 
        - ABS(COALESCE(t.size_sqft, 0) - COALESCE(p_size_sqft, 0)) * 0.01 as similarity_score
    FROM transactions t
    WHERE t.community ILIKE '%' || p_community || '%'
      AND (p_property_type IS NULL OR t.property_type ILIKE '%' || p_property_type || '%')
      AND t.transaction_date >= v_cutoff_date
      AND t.price > 0
    ORDER BY similarity_score DESC, t.transaction_date DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 3. SEARCH OWNERS (Fixed: BIGINT for owner_id instead of UUID)
-- ============================================================
CREATE OR REPLACE FUNCTION search_owners(
    p_query TEXT,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    owner_id BIGINT,
    owner_name TEXT,
    owner_phone TEXT,
    property_count BIGINT,
    total_portfolio_value DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.id,
        o.norm_name,
        o.norm_phone,
        COUNT(p.id)::BIGINT as property_count,
        SUM(p.last_price) as total_portfolio_value
    FROM owners o
    LEFT JOIN properties p ON p.owner_id = o.id
    WHERE o.norm_name ILIKE '%' || p_query || '%'
       OR o.norm_phone ILIKE '%' || p_query || '%'
    GROUP BY o.id, o.norm_name, o.norm_phone
    ORDER BY property_count DESC, total_portfolio_value DESC NULLS LAST
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
