-- ============================================================
-- SUPABASE RPC FUNCTIONS FOR DUBAI REAL ESTATE ANALYTICS
-- ============================================================
-- These functions can be called via Supabase client:
-- supabase.rpc('function_name', { params })

-- ============================================================
-- 1. MARKET STATISTICS
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
-- 2. TOP INVESTORS BY PORTFOLIO VALUE
-- ============================================================
CREATE OR REPLACE FUNCTION top_investors(
    p_community TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_min_properties INTEGER DEFAULT 2
)
RETURNS TABLE (
    owner_name TEXT,
    owner_phone TEXT,
    total_properties BIGINT,
    portfolio_value NUMERIC,
    avg_property_price NUMERIC,
    communities TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH owner_stats AS (
        SELECT 
            o.norm_name,
            o.norm_phone,
            COUNT(DISTINCT p.id)::BIGINT as prop_count,
            SUM(p.last_price) as total_value,
            ARRAY_AGG(DISTINCT p.community) as comm_list
        FROM owners o
        JOIN properties p ON p.owner_id = o.id
        WHERE p.last_price IS NOT NULL
          AND (p_community IS NULL OR p.community ILIKE '%' || p_community || '%')
        GROUP BY o.id, o.norm_name, o.norm_phone
        HAVING COUNT(DISTINCT p.id) >= p_min_properties
    )
    SELECT 
        norm_name,
        norm_phone,
        prop_count,
        ROUND(total_value, 2) as portfolio_value,
        ROUND(total_value / prop_count, 2) as avg_property_price,
        comm_list
    FROM owner_stats
    ORDER BY total_value DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 3. OWNER PORTFOLIO DETAILS
-- ============================================================
CREATE OR REPLACE FUNCTION owner_portfolio(
    p_owner_name TEXT DEFAULT NULL,
    p_owner_phone TEXT DEFAULT NULL
)
RETURNS TABLE (
    owner_name TEXT,
    owner_phone TEXT,
    property_community TEXT,
    property_building TEXT,
    property_unit TEXT,
    property_type TEXT,
    bedrooms INTEGER,
    size_sqft NUMERIC,
    last_price NUMERIC,
    last_transaction_date DATE,
    purchase_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.norm_name,
        o.norm_phone,
        p.community,
        p.building,
        p.unit,
        p.type,
        p.bedrooms,
        p.size_sqft,
        p.last_price,
        p.last_transaction_date,
        (
            SELECT COUNT(*)::INTEGER 
            FROM transactions t 
            WHERE t.community = p.community 
              AND t.building = p.building 
              AND t.unit = p.unit
        ) as purchase_count
    FROM owners o
    JOIN properties p ON p.owner_id = o.id
    WHERE (p_owner_name IS NULL OR o.norm_name ILIKE '%' || p_owner_name || '%')
      AND (p_owner_phone IS NULL OR o.norm_phone = p_owner_phone)
    ORDER BY p.last_price DESC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 4. FIND COMPARABLE PROPERTIES
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
-- 5. TRANSACTION VELOCITY (transactions per month)
-- ============================================================
CREATE OR REPLACE FUNCTION transaction_velocity(
    p_community TEXT DEFAULT NULL,
    p_months INTEGER DEFAULT 12
)
RETURNS TABLE (
    year_month TEXT,
    transaction_count BIGINT,
    total_volume NUMERIC,
    avg_price NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        TO_CHAR(transaction_date, 'YYYY-MM') as year_month,
        COUNT(*)::BIGINT as transaction_count,
        SUM(price) as total_volume,
        ROUND(AVG(price), 2) as avg_price
    FROM transactions
    WHERE (p_community IS NULL OR community ILIKE '%' || p_community || '%')
      AND transaction_date >= CURRENT_DATE - (p_months || ' months')::INTERVAL
      AND price > 0
    GROUP BY year_month
    ORDER BY year_month DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 6. SEASONAL PATTERNS
-- ============================================================
CREATE OR REPLACE FUNCTION seasonal_patterns(
    p_community TEXT DEFAULT NULL
)
RETURNS TABLE (
    month_number INTEGER,
    month_name TEXT,
    avg_transactions NUMERIC,
    avg_price NUMERIC,
    total_volume NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        EXTRACT(MONTH FROM transaction_date)::INTEGER as month_number,
        TO_CHAR(transaction_date, 'Month') as month_name,
        COUNT(*)::NUMERIC / COUNT(DISTINCT EXTRACT(YEAR FROM transaction_date)) as avg_transactions,
        ROUND(AVG(price), 2) as avg_price,
        SUM(price) as total_volume
    FROM transactions
    WHERE (p_community IS NULL OR community ILIKE '%' || p_community || '%')
      AND price > 0
    GROUP BY month_number, month_name
    ORDER BY month_number;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 7. LIKELY SELLERS (properties owned 3+ years)
-- ============================================================
CREATE OR REPLACE FUNCTION likely_sellers(
    p_community TEXT DEFAULT NULL,
    p_min_years_owned INTEGER DEFAULT 3,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    owner_name TEXT,
    owner_phone TEXT,
    property_community TEXT,
    property_building TEXT,
    property_unit TEXT,
    property_type TEXT,
    bedrooms INTEGER,
    last_price NUMERIC,
    years_owned NUMERIC,
    last_transaction_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.norm_name,
        o.norm_phone,
        p.community,
        p.building,
        p.unit,
        p.type,
        p.bedrooms,
        p.last_price,
        ROUND(EXTRACT(EPOCH FROM (CURRENT_DATE - p.last_transaction_date)) / 31536000, 1) as years_owned,
        p.last_transaction_date
    FROM owners o
    JOIN properties p ON p.owner_id = o.id
    WHERE (p_community IS NULL OR p.community ILIKE '%' || p_community || '%')
      AND p.last_transaction_date IS NOT NULL
      AND p.last_transaction_date <= CURRENT_DATE - (p_min_years_owned || ' years')::INTERVAL
    ORDER BY years_owned DESC, p.last_price DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 8. COMMUNITY COMPARISON
-- ============================================================
CREATE OR REPLACE FUNCTION compare_communities(
    p_communities TEXT[]
)
RETURNS TABLE (
    community TEXT,
    total_transactions BIGINT,
    avg_price NUMERIC,
    median_price NUMERIC,
    total_volume NUMERIC,
    avg_price_per_sqft NUMERIC,
    most_common_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.community,
        COUNT(*)::BIGINT as total_transactions,
        ROUND(AVG(t.price), 2) as avg_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.price) as median_price,
        SUM(t.price) as total_volume,
        ROUND(AVG(t.price / NULLIF(t.size_sqft, 0)), 2) as avg_price_per_sqft,
        MODE() WITHIN GROUP (ORDER BY t.property_type) as most_common_type
    FROM transactions t
    WHERE EXISTS (
        SELECT 1 FROM unnest(p_communities) comm 
        WHERE t.community ILIKE '%' || comm || '%'
    )
    AND t.price > 0
    GROUP BY t.community
    ORDER BY total_transactions DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 9. PROPERTY TRANSACTION HISTORY
-- ============================================================
CREATE OR REPLACE FUNCTION property_history(
    p_community TEXT,
    p_building TEXT,
    p_unit TEXT
)
RETURNS TABLE (
    transaction_date DATE,
    price NUMERIC,
    price_per_sqft NUMERIC,
    seller_name TEXT,
    buyer_name TEXT,
    property_type TEXT,
    size_sqft NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.transaction_date,
        t.price,
        ROUND(t.price / NULLIF(t.size_sqft, 0), 2) as price_per_sqft,
        t.seller_name,
        t.buyer_name,
        t.property_type,
        t.size_sqft
    FROM transactions t
    WHERE t.community ILIKE '%' || p_community || '%'
      AND t.building ILIKE '%' || p_building || '%'
      AND t.unit ILIKE '%' || p_unit || '%'
    ORDER BY t.transaction_date DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 10. SEARCH OWNERS
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
