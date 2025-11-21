-- ============================================================
-- DATABASE STATS FUNCTION FOR HEALTH CHECKS
-- ============================================================
-- Returns general database statistics including property counts
-- and embedding coverage

CREATE OR REPLACE FUNCTION public.db_stats()
RETURNS TABLE (
    property_count BIGINT,
    transaction_count BIGINT,
    owner_count BIGINT,
    avg_price_per_sqft NUMERIC,
    chunks_count BIGINT,
    properties_with_embeddings BIGINT,
    chunks_with_embeddings BIGINT,
    last_update TIMESTAMPTZ
) AS $$
DECLARE
    chunk_table TEXT;
    chunk_query TEXT;
    chunk_records BIGINT := 0;
    properties_with_vectors BIGINT := 0;
    chunk_vectors BIGINT := 0;
    chunk_updated TIMESTAMPTZ := NULL;
BEGIN
    IF to_regclass('public.chunks') IS NOT NULL THEN
        chunk_table := 'public.chunks';
    ELSIF to_regclass('public.property_chunks') IS NOT NULL THEN
        chunk_table := 'public.property_chunks';
    END IF;

    IF chunk_table IS NOT NULL THEN
        chunk_query := format('SELECT COUNT(*) FROM %s', chunk_table);
        EXECUTE chunk_query INTO chunk_records;

        chunk_query := format('SELECT COUNT(DISTINCT property_id) FROM %s WHERE embedding IS NOT NULL', chunk_table);
        EXECUTE chunk_query INTO properties_with_vectors;

        chunk_query := format('SELECT COUNT(*) FROM %s WHERE embedding IS NOT NULL', chunk_table);
        EXECUTE chunk_query INTO chunk_vectors;

        chunk_query := format('SELECT MAX(created_at) FROM %s WHERE embedding IS NOT NULL', chunk_table);
        EXECUTE chunk_query INTO chunk_updated;
    END IF;

    IF properties_with_vectors = 0 THEN
        properties_with_vectors := (
            SELECT COUNT(*)
            FROM properties
            WHERE description_embedding IS NOT NULL OR image_embedding IS NOT NULL
        );
    END IF;

    IF chunk_updated IS NULL THEN
        chunk_updated := (
            SELECT MAX(embedding_generated_at) FROM properties WHERE embedding_generated_at IS NOT NULL
        );
    END IF;

    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM properties)::BIGINT as property_count,
        (SELECT COUNT(*) FROM transactions)::BIGINT as transaction_count,
        (SELECT COUNT(*) FROM owners)::BIGINT as owner_count,
        ROUND(
            (SELECT AVG(price / NULLIF(size_sqft, 0)) 
             FROM transactions 
             WHERE price > 0 AND size_sqft > 0), 2
        ) as avg_price_per_sqft,
        COALESCE(chunk_records, 0)::BIGINT as chunks_count,
        properties_with_vectors::BIGINT as properties_with_embeddings,
        chunk_vectors::BIGINT as chunks_with_embeddings,
        chunk_updated as last_update;
END;
$$ LANGUAGE plpgsql
STABLE
SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.db_stats TO anon, authenticated, service_role;
