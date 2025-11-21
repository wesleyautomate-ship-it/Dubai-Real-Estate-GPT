-- Add embedding support to properties table
-- Allows direct semantic search on properties table (alternative to chunks)

-- Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding columns to properties table
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS description_embedding vector(1536);

ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS embedding_model TEXT;

ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMPTZ;

-- Create IVFFLAT index for vector similarity search on properties
-- lists=100 works well for datasets up to 1M rows
CREATE INDEX IF NOT EXISTS idx_properties_embedding 
ON properties USING ivfflat (description_embedding vector_cosine_ops) 
WITH (lists = 100);

-- Add comments
COMMENT ON COLUMN properties.description_embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions) for property description';
COMMENT ON COLUMN properties.embedding_model IS 'Model used to generate embedding (e.g., text-embedding-3-small)';
COMMENT ON COLUMN properties.embedding_generated_at IS 'Timestamp when embedding was generated';

-- After running this migration, populate embeddings with:
-- python backend/scripts/populate_property_embeddings.py
