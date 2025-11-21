-- RPC Function to Check pgvector Extension Status
-- Run this in Supabase SQL Editor to create the function
-- Then call it via REST API: POST /rest/v1/rpc/check_pgvector

CREATE OR REPLACE FUNCTION public.check_pgvector()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result jsonb;
    ext_record record;
    avail_record record;
    vector_cols int;
BEGIN
    -- Initialize result object
    result := jsonb_build_object(
        'timestamp', now(),
        'database', current_database(),
        'pgvector_installed', false,
        'pgvector_version', null,
        'pgvector_available', false,
        'available_version', null,
        'vector_type_exists', false,
        'vector_columns_count', 0,
        'vector_operators', jsonb_build_array()
    );
    
    -- Check if pgvector extension is installed
    SELECT extname, extversion INTO ext_record
    FROM pg_extension
    WHERE extname = 'vector';
    
    IF FOUND THEN
        result := jsonb_set(result, '{pgvector_installed}', 'true'::jsonb);
        result := jsonb_set(result, '{pgvector_version}', to_jsonb(ext_record.extversion));
    END IF;
    
    -- Check if pgvector is available (can be installed)
    SELECT name, default_version, installed_version INTO avail_record
    FROM pg_available_extensions
    WHERE name = 'vector';
    
    IF FOUND THEN
        result := jsonb_set(result, '{pgvector_available}', 'true'::jsonb);
        result := jsonb_set(result, '{available_version}', to_jsonb(avail_record.default_version));
    END IF;
    
    -- Check if vector type exists
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
        result := jsonb_set(result, '{vector_type_exists}', 'true'::jsonb);
    END IF;
    
    -- Count columns using vector type
    SELECT count(*) INTO vector_cols
    FROM information_schema.columns
    WHERE udt_name = 'vector';
    
    result := jsonb_set(result, '{vector_columns_count}', to_jsonb(vector_cols));
    
    -- Check for vector operators (similarity functions)
    IF result->>'pgvector_installed' = 'true' THEN
        result := jsonb_set(result, '{vector_operators}', (
            SELECT jsonb_agg(oprname ORDER BY oprname)
            FROM pg_operator
            WHERE oprleft = (SELECT oid FROM pg_type WHERE typname = 'vector')
               OR oprright = (SELECT oid FROM pg_type WHERE typname = 'vector')
            LIMIT 10
        ));
    END IF;
    
    RETURN result;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.check_pgvector() TO anon, authenticated, service_role;

-- Example usage:
-- SELECT check_pgvector();

COMMENT ON FUNCTION public.check_pgvector() IS 
'Check if pgvector extension is installed and available. Returns detailed status as JSON.';
