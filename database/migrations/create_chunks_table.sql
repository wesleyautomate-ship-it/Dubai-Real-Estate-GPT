-- Create chunks table for property text embeddings
-- This table stores semantic embeddings of property descriptions for vector search

-- Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    property_id BIGINT REFERENCES properties(id) ON DELETE CASCADE,
    chunk_type TEXT DEFAULT 'property_description',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on property_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_chunks_property_id ON chunks(property_id);

-- Create index on chunk_type for filtering
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);

-- Create IVFFLAT index for vector similarity search
-- Note: This index is created AFTER data is loaded for optimal performance
-- lists=100 is a good starting point (adjust based on data size)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
ON chunks USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Add comment for documentation
COMMENT ON TABLE chunks IS 'Stores text chunks and their embeddings for semantic property search';
COMMENT ON COLUMN chunks.embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions)';
COMMENT ON COLUMN chunks.content IS 'Natural language description of the property';
COMMENT ON COLUMN chunks.metadata IS 'Additional metadata: embedding_model, generated_at, source, etc.';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON chunks TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON chunks TO service_role;
GRANT USAGE, SELECT ON SEQUENCE chunks_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE chunks_id_seq TO service_role;
