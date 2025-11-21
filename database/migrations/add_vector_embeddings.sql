-- Migration: Add Vector Embedding Support
-- Prerequisites: pgvector extension must be enabled
-- Run: CREATE EXTENSION IF NOT EXISTS vector; (if not already enabled)

-- =============================================================================
-- STEP 1: Enable pgvector extension
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- STEP 2: Add embedding columns to properties table
-- =============================================================================

-- Property description embeddings (OpenAI ada-002: 1536 dimensions)
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS description_embedding vector(1536);

-- Property image embeddings (CLIP: 512 dimensions)
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS image_embedding vector(512);

-- Metadata: when embeddings were generated
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS embedding_generated_at timestamptz;

ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'text-embedding-ada-002';

COMMENT ON COLUMN properties.description_embedding IS 
'Vector embedding of property description for semantic search (1536-dim from OpenAI ada-002)';

COMMENT ON COLUMN properties.image_embedding IS 
'Vector embedding of property images for visual similarity search (512-dim from CLIP)';

COMMENT ON COLUMN properties.embedding_generated_at IS 
'Timestamp when embeddings were last generated';

COMMENT ON COLUMN properties.embedding_model IS 
'Name of the embedding model used (e.g., text-embedding-ada-002)';

-- =============================================================================
-- STEP 3: Create indexes for fast similarity search
-- =============================================================================

-- IVFFlat index for description embeddings (cosine similarity)
-- Lists parameter: sqrt(total_rows) is a good starting point
-- For 10,000 properties: lists = 100
-- For 100,000 properties: lists = 300
CREATE INDEX IF NOT EXISTS idx_properties_description_embedding 
ON properties 
USING ivfflat (description_embedding vector_cosine_ops)
WITH (lists = 100);

-- IVFFlat index for image embeddings (cosine similarity)
CREATE INDEX IF NOT EXISTS idx_properties_image_embedding 
ON properties 
USING ivfflat (image_embedding vector_cosine_ops)
WITH (lists = 100);

-- =============================================================================
-- STEP 4: Create helper function to check embedding status
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_embedding_stats()
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'total_properties', COUNT(*),
        'with_description_embedding', COUNT(description_embedding),
        'with_image_embedding', COUNT(image_embedding),
        'embedding_coverage_pct', 
            ROUND((COUNT(description_embedding)::numeric / NULLIF(COUNT(*), 0)) * 100, 2),
        'latest_embedding_date', MAX(embedding_generated_at),
        'embedding_models', jsonb_agg(DISTINCT embedding_model)
    ) INTO result
    FROM properties;
    
    RETURN result;
END;
$$;

COMMENT ON FUNCTION public.get_embedding_stats() IS 
'Returns statistics about embedding coverage in the properties table';

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.get_embedding_stats() TO anon, authenticated, service_role;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Check that columns were added
SELECT 
    column_name, 
    data_type, 
    udt_name
FROM information_schema.columns
WHERE table_name = 'properties' 
    AND column_name LIKE '%embedding%'
ORDER BY ordinal_position;

-- Check indexes
SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename = 'properties' 
    AND indexname LIKE '%embedding%';

-- Check embedding stats
SELECT get_embedding_stats();

-- Expected output:
-- {
--   "total_properties": 12345,
--   "with_description_embedding": 0,
--   "with_image_embedding": 0,
--   "embedding_coverage_pct": 0.00,
--   "latest_embedding_date": null,
--   "embedding_models": [null]
-- }
