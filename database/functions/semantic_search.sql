-- Semantic Property Search RPC Function
-- Enables natural language property search using vector embeddings

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
    property_id text,
    community text,
    building_name text,
    bedrooms int,
    size_sqft numeric,
    price_aed numeric,
    price_per_sqft numeric,
    property_type text,
    similarity float,
    distance float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.property_id,
        p.community,
        p.building_name,
        p.bedrooms,
        p.size_sqft,
        p.price_aed,
        (p.price_aed / NULLIF(p.size_sqft, 0))::numeric AS price_per_sqft,
        p.property_type,
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
        AND (filter_min_price IS NULL OR p.price_aed >= filter_min_price)
        AND (filter_max_price IS NULL OR p.price_aed <= filter_max_price)
        AND (filter_bedrooms IS NULL OR p.bedrooms = filter_bedrooms)
    ORDER BY p.description_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.search_properties_semantic IS 
'Semantic property search using vector embeddings. Finds properties similar to a natural language query.';

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.search_properties_semantic TO anon, authenticated, service_role;


-- =============================================================================
-- Similar Properties Function (find properties like a given property)
-- =============================================================================

CREATE OR REPLACE FUNCTION public.find_similar_properties(
    target_property_id text,
    match_count int DEFAULT 10,
    min_similarity float DEFAULT 0.7
)
RETURNS TABLE (
    property_id text,
    community text,
    building_name text,
    bedrooms int,
    size_sqft numeric,
    price_aed numeric,
    price_per_sqft numeric,
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
    WHERE properties.property_id = target_property_id;
    
    -- Check if embedding exists
    IF target_embedding IS NULL THEN
        RAISE EXCEPTION 'Property % has no embedding', target_property_id;
    END IF;
    
    -- Find similar properties
    RETURN QUERY
    SELECT 
        p.property_id,
        p.community,
        p.building_name,
        p.bedrooms,
        p.size_sqft,
        p.price_aed,
        (p.price_aed / NULLIF(p.size_sqft, 0))::numeric AS price_per_sqft,
        (1 - (p.description_embedding <=> target_embedding))::float AS similarity
    FROM properties p
    WHERE 
        p.property_id != target_property_id  -- Exclude the target property itself
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
-- Hybrid Search Function (combines text search with semantic search)
-- =============================================================================

CREATE OR REPLACE FUNCTION public.hybrid_property_search(
    search_query text,
    query_embedding vector(1536) DEFAULT NULL,
    semantic_weight float DEFAULT 0.5,
    match_count int DEFAULT 20
)
RETURNS TABLE (
    property_id text,
    community text,
    building_name text,
    bedrooms int,
    price_aed numeric,
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
            p.property_id,
            ts_rank(
                to_tsvector('english', 
                    COALESCE(p.community, '') || ' ' || 
                    COALESCE(p.building_name, '') || ' ' || 
                    COALESCE(p.property_type, '')
                ),
                plainto_tsquery('english', search_query)
            ) AS text_score
        FROM properties p
        WHERE to_tsvector('english', 
            COALESCE(p.community, '') || ' ' || 
            COALESCE(p.building_name, '') || ' ' || 
            COALESCE(p.property_type, '')
        ) @@ plainto_tsquery('english', search_query)
    ),
    semantic_search AS (
        SELECT 
            p.property_id,
            (1 - (p.description_embedding <=> query_embedding))::float AS semantic_score
        FROM properties p
        WHERE query_embedding IS NOT NULL
            AND p.description_embedding IS NOT NULL
    )
    SELECT 
        p.property_id,
        p.community,
        p.building_name,
        p.bedrooms,
        p.price_aed,
        (
            COALESCE(ts.text_score, 0) * (1 - semantic_weight) + 
            COALESCE(ss.semantic_score, 0) * semantic_weight
        )::float AS combined_score,
        COALESCE(ts.text_score, 0)::float AS text_score,
        COALESCE(ss.semantic_score, 0)::float AS semantic_score
    FROM properties p
    LEFT JOIN text_search ts ON ts.property_id = p.property_id
    LEFT JOIN semantic_search ss ON ss.property_id = p.property_id
    WHERE ts.property_id IS NOT NULL OR ss.property_id IS NOT NULL
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.hybrid_property_search IS 
'Hybrid search combining traditional text search with semantic vector search';

GRANT EXECUTE ON FUNCTION public.hybrid_property_search TO anon, authenticated, service_role;


-- =============================================================================
-- Example Usage
-- =============================================================================

-- Example 1: Semantic search with natural language query
-- (Note: You need to generate the embedding first using OpenAI)
/*
SELECT * FROM search_properties_semantic(
    query_embedding := '[0.1, 0.2, ..., 0.5]'::vector(1536),
    match_threshold := 0.75,
    match_count := 10,
    filter_community := 'Dubai Marina',
    filter_min_price := 1000000,
    filter_max_price := 3000000
);
*/

-- Example 2: Find similar properties
/*
SELECT * FROM find_similar_properties(
    target_property_id := 'PROP12345',
    match_count := 5,
    min_similarity := 0.8
);
*/

-- Example 3: Hybrid search
/*
SELECT * FROM hybrid_property_search(
    search_query := 'luxury apartment marina view',
    query_embedding := '[0.1, 0.2, ..., 0.5]'::vector(1536),
    semantic_weight := 0.6,
    match_count := 15
);
*/
