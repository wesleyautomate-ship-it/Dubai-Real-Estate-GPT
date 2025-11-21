-- CORRECTED Semantic Property Search RPC Functions (v2)
-- Drops old functions first, then creates new ones with correct schema

-- =============================================================================
-- DROP OLD FUNCTIONS FIRST
-- =============================================================================

DROP FUNCTION IF EXISTS public.search_properties_semantic(vector, float, int, text, numeric, numeric, int);
DROP FUNCTION IF EXISTS public.find_similar_properties(text, int, float);
DROP FUNCTION IF EXISTS public.find_similar_properties(bigint, int, float);
DROP FUNCTION IF EXISTS public.hybrid_property_search(text, vector, float, int);

-- =============================================================================
-- Main Semantic Search Function
-- =============================================================================

CREATE OR REPLACE FUNCTION public.search_properties_semantic(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    filter_community text DEFAULT NULL,
    filter_min_price numeric DEFAULT NULL,
    filter_max_price numeric DEFAULT NULL,
    filter_bedrooms int DEFAULT NULL
)
RETURNS TABLE (
    id bigint,
    community text,
    building text,
    unit text,
    bedrooms numeric,
    bathrooms numeric,
    size_sqft numeric,
    last_price numeric,
    price_per_sqft numeric,
    type text,
    similarity float,
    distance float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.community,
        p.building,
        p.unit,
        p.bedrooms,
        p.bathrooms,
        p.size_sqft,
        p.last_price,
        (p.last_price / NULLIF(p.size_sqft, 0))::numeric AS price_per_sqft,
        p.type,
        (1 - (p.description_embedding <=> query_embedding))::float AS similarity,
        (p.description_embedding <=> query_embedding)::float AS distance
    FROM properties p
    WHERE 
        -- Must have embedding
        p.description_embedding IS NOT NULL
        -- Similarity threshold
        AND (1 - (p.description_embedding <=> query_embedding)) > match_threshold
        -- Optional filters
        AND (filter_community IS NULL OR p.community = filter_community)
        AND (filter_min_price IS NULL OR p.last_price >= filter_min_price)
        AND (filter_max_price IS NULL OR p.last_price <= filter_max_price)
        AND (filter_bedrooms IS NULL OR p.bedrooms = filter_bedrooms)
    ORDER BY p.description_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.search_properties_semantic IS 
'Semantic property search using vector embeddings. Finds properties similar to a natural language query.';

GRANT EXECUTE ON FUNCTION public.search_properties_semantic TO anon, authenticated, service_role;


-- =============================================================================
-- Find Similar Properties Function
-- =============================================================================

CREATE OR REPLACE FUNCTION public.find_similar_properties(
    target_property_id bigint,
    match_count int DEFAULT 10,
    min_similarity float DEFAULT 0.7
)
RETURNS TABLE (
    id bigint,
    community text,
    building text,
    unit text,
    bedrooms numeric,
    bathrooms numeric,
    size_sqft numeric,
    last_price numeric,
    price_per_sqft numeric,
    type text,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    target_embedding vector(1536);
BEGIN
    -- Get the embedding of the target property
    SELECT description_embedding INTO target_embedding
    FROM properties
    WHERE properties.id = target_property_id;
    
    -- Check if embedding exists
    IF target_embedding IS NULL THEN
        RAISE EXCEPTION 'Property % has no embedding', target_property_id;
    END IF;
    
    -- Find similar properties
    RETURN QUERY
    SELECT 
        p.id,
        p.community,
        p.building,
        p.unit,
        p.bedrooms,
        p.bathrooms,
        p.size_sqft,
        p.last_price,
        (p.last_price / NULLIF(p.size_sqft, 0))::numeric AS price_per_sqft,
        p.type,
        (1 - (p.description_embedding <=> target_embedding))::float AS similarity
    FROM properties p
    WHERE 
        p.id != target_property_id  -- Exclude the target property itself
        AND p.description_embedding IS NOT NULL
        AND (1 - (p.description_embedding <=> target_embedding)) >= min_similarity
    ORDER BY p.description_embedding <=> target_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.find_similar_properties IS 
'Find properties similar to a given property using vector embeddings';

GRANT EXECUTE ON FUNCTION public.find_similar_properties TO anon, authenticated, service_role;


-- =============================================================================
-- Hybrid Search Function (Text + Semantic)
-- =============================================================================

CREATE OR REPLACE FUNCTION public.hybrid_property_search(
    search_query text,
    query_embedding vector(1536) DEFAULT NULL,
    semantic_weight float DEFAULT 0.5,
    match_count int DEFAULT 20
)
RETURNS TABLE (
    id bigint,
    community text,
    building text,
    unit text,
    bedrooms numeric,
    last_price numeric,
    type text,
    combined_score float,
    text_score float,
    semantic_score float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH text_search AS (
        SELECT 
            p.id,
            ts_rank(
                to_tsvector('english', 
                    COALESCE(p.community, '') || ' ' || 
                    COALESCE(p.building, '') || ' ' || 
                    COALESCE(p.type, '')
                ),
                plainto_tsquery('english', search_query)
            ) AS text_score
        FROM properties p
        WHERE to_tsvector('english', 
            COALESCE(p.community, '') || ' ' || 
            COALESCE(p.building, '') || ' ' || 
            COALESCE(p.type, '')
        ) @@ plainto_tsquery('english', search_query)
    ),
    semantic_search AS (
        SELECT 
            p.id,
            (1 - (p.description_embedding <=> query_embedding))::float AS semantic_score
        FROM properties p
        WHERE query_embedding IS NOT NULL
            AND p.description_embedding IS NOT NULL
    )
    SELECT 
        p.id,
        p.community,
        p.building,
        p.unit,
        p.bedrooms,
        p.last_price,
        p.type,
        (
            COALESCE(ts.text_score, 0) * (1 - semantic_weight) + 
            COALESCE(ss.semantic_score, 0) * semantic_weight
        )::float AS combined_score,
        COALESCE(ts.text_score, 0)::float AS text_score,
        COALESCE(ss.semantic_score, 0)::float AS semantic_score
    FROM properties p
    LEFT JOIN text_search ts ON ts.id = p.id
    LEFT JOIN semantic_search ss ON ss.id = p.id
    WHERE ts.id IS NOT NULL OR ss.id IS NOT NULL
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.hybrid_property_search IS 
'Hybrid search combining traditional text search with semantic vector search';

GRANT EXECUTE ON FUNCTION public.hybrid_property_search TO anon, authenticated, service_role;


-- =============================================================================
-- Verify Functions Were Created
-- =============================================================================

SELECT 
    routine_name as function_name,
    routine_type as type
FROM information_schema.routines
WHERE routine_schema = 'public'
    AND routine_name IN (
        'search_properties_semantic',
        'find_similar_properties',
        'hybrid_property_search'
    )
ORDER BY routine_name;

-- Success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ All search functions updated successfully!';
    RAISE NOTICE '📊 Functions now use correct column names: id, building, last_price, type';
    RAISE NOTICE '🎯 Ready to use after embeddings are generated';
END $$;
