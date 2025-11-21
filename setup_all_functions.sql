-- =============================================================================
-- COMPLETE SETUP SCRIPT FOR DUBAI REAL ESTATE SEARCH
-- Run this entire script in your Supabase SQL Editor
-- =============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- TABLE: chunks or property_chunks (if it doesn't exist)
-- =============================================================================
CREATE TABLE IF NOT EXISTS chunks (
    id bigserial primary key,
    property_id bigint references properties(id),
    content text,
    embedding vector(1536),
    created_at timestamptz default now()
);

CREATE INDEX IF NOT EXISTS chunks_property_id_idx ON chunks(property_id);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING ivfflat (embedding vector_cosine_ops);

-- =============================================================================
-- 1. semantic_search_chunks - Search chunks table with filters
-- =============================================================================
CREATE OR REPLACE FUNCTION public.semantic_search_chunks(
    query_embedding vector(1536),
    match_threshold double precision DEFAULT 0.75,
    match_count int DEFAULT 12,
    filter_community text DEFAULT NULL,
    min_size numeric DEFAULT NULL,
    max_size numeric DEFAULT NULL,
    filter_bedrooms int DEFAULT NULL,
    min_price numeric DEFAULT NULL,
    max_price numeric DEFAULT NULL
)
RETURNS TABLE (
    chunk_id bigint,
    property_id bigint,
    content text,
    score double precision,
    community text,
    building text,
    unit text,
    bedrooms numeric,
    size_sqft numeric,
    price_aed numeric,
    owner_name text,
    owner_phone text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        c.id as chunk_id,
        c.property_id,
        c.content,
        (1 - (c.embedding <=> query_embedding))::double precision as score,
        p.community,
        p.building,
        p.unit,
        p.bedrooms,
        p.size_sqft,
        COALESCE(p.last_price, t.price) as price_aed,
        COALESCE(t.buyer_name, 'N/A') as owner_name,
        COALESCE(t.buyer_phone, 'N/A') as owner_phone
    FROM chunks c
    JOIN properties p ON p.id = c.property_id
    LEFT JOIN LATERAL (
        SELECT buyer_name, buyer_phone, price
        FROM transactions
        WHERE community = p.community 
          AND building = p.building 
          AND unit = p.unit
        ORDER BY transaction_date DESC
        LIMIT 1
    ) t ON true
    WHERE
        c.embedding IS NOT NULL
        AND (1 - (c.embedding <=> query_embedding)) >= match_threshold
        AND (filter_community IS NULL OR p.community ILIKE '%' || filter_community || '%')
        AND (min_size IS NULL OR p.size_sqft >= min_size)
        AND (max_size IS NULL OR p.size_sqft <= max_size)
        AND (filter_bedrooms IS NULL OR p.bedrooms = filter_bedrooms)
        AND (min_price IS NULL OR COALESCE(p.last_price, t.price) >= min_price)
        AND (max_price IS NULL OR COALESCE(p.last_price, t.price) <= max_price)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

COMMENT ON FUNCTION public.semantic_search_chunks IS 
'Semantic search on chunks table using vector embeddings with optional filters';

GRANT EXECUTE ON FUNCTION public.semantic_search_chunks TO anon, authenticated, service_role;


-- =============================================================================
-- 2. db_stats - Database statistics
-- =============================================================================
CREATE OR REPLACE FUNCTION public.db_stats()
RETURNS TABLE (
    property_count bigint,
    transaction_count bigint,
    owner_count bigint,
    avg_price_per_sqft numeric,
    chunks_count bigint,
    properties_with_embeddings bigint,
    chunks_with_embeddings bigint,
    last_update timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        (SELECT COUNT(*) FROM properties)::bigint as property_count,
        (SELECT COUNT(*) FROM transactions)::bigint as transaction_count,
        (SELECT COUNT(*) FROM owners)::bigint as owner_count,
        (SELECT ROUND(AVG(price / NULLIF(size_sqft, 0)), 2) 
         FROM transactions 
         WHERE price > 0 AND size_sqft > 0)::numeric as avg_price_per_sqft,
        CASE
            WHEN to_regclass('public.chunks') IS NOT NULL THEN
                (SELECT COUNT(*) FROM chunks)
            WHEN to_regclass('public.property_chunks') IS NOT NULL THEN
                (SELECT COUNT(*) FROM property_chunks)
            ELSE 0
        END::bigint as chunks_count,
        CASE
            WHEN to_regclass('public.chunks') IS NOT NULL THEN
                (SELECT COUNT(DISTINCT property_id) FROM chunks WHERE embedding IS NOT NULL)
            WHEN to_regclass('public.property_chunks') IS NOT NULL THEN
                (SELECT COUNT(DISTINCT property_id) FROM property_chunks WHERE embedding IS NOT NULL)
            ELSE
                (
                    SELECT COUNT(*)
                    FROM properties
                    WHERE description_embedding IS NOT NULL OR image_embedding IS NOT NULL
                )
        END::bigint as properties_with_embeddings,
        CASE
            WHEN to_regclass('public.chunks') IS NOT NULL THEN
                (SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL)
            WHEN to_regclass('public.property_chunks') IS NOT NULL THEN
                (SELECT COUNT(*) FROM property_chunks WHERE embedding IS NOT NULL)
            ELSE 0
        END::bigint as chunks_with_embeddings,
        CASE
            WHEN to_regclass('public.chunks') IS NOT NULL THEN
                (SELECT MAX(created_at) FROM chunks WHERE embedding IS NOT NULL)
            WHEN to_regclass('public.property_chunks') IS NOT NULL THEN
                (SELECT MAX(created_at) FROM property_chunks WHERE embedding IS NOT NULL)
            ELSE
                (SELECT MAX(embedding_generated_at) FROM properties WHERE embedding_generated_at IS NOT NULL)
        END as last_update;
$$;

COMMENT ON FUNCTION public.db_stats IS 
'Returns database statistics including property count, embeddings coverage, and last update time';

GRANT EXECUTE ON FUNCTION public.db_stats TO anon, authenticated, service_role;


-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ All functions created successfully!';
    RAISE NOTICE '📊 Available RPC functions:';
    RAISE NOTICE '   - semantic_search_chunks(query_embedding, ...)';
    RAISE NOTICE '   - db_stats()';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  Note: You need to populate the chunks table with embeddings';
    RAISE NOTICE '   before semantic search will return results.';
END $$;
