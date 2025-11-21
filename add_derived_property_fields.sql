-- =============================================================================
-- ADD DERIVED PROPERTY TYPE AND BEDROOM FIELDS
-- Based on unit naming patterns and existing data
-- =============================================================================

-- Step 1: Add new columns if they don't exist
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS property_type_derived text,
ADD COLUMN IF NOT EXISTS bedrooms_estimated int;

-- Step 2: Create function to derive property type from unit and building
CREATE OR REPLACE FUNCTION derive_property_type(
    unit_val text,
    building_val text,
    type_val text,
    community_val text,
    size_sqft_val numeric
) RETURNS text AS $$
BEGIN
    -- Villa indicators
    IF building_val IS NULL OR building_val = '' THEN
        -- Empty building usually means villa
        RETURN 'Villa';
    END IF;
    
    -- Check unit prefix patterns
    IF unit_val ILIKE 'v%' OR unit_val ILIKE 'villa%' THEN
        RETURN 'Villa';
    END IF;
    
    IF unit_val ILIKE 'th%' OR unit_val ILIKE 'town%' THEN
        RETURN 'Townhouse';
    END IF;
    
    -- Check if it's land but small (likely villa)
    IF type_val ILIKE '%land%' AND size_sqft_val IS NOT NULL AND size_sqft_val < 5382 THEN
        -- Less than 5000 sqm (≈ 5382 sqft) is probably a villa
        RETURN 'Villa';
    END IF;
    
    -- Specific villa communities
    IF community_val ILIKE '%arabian ranches%' 
        OR community_val ILIKE '%damac%' 
        OR community_val ILIKE '%lagoon%' THEN
        RETURN 'Villa';
    END IF;
    
    -- If type says land
    IF type_val ILIKE '%land%' THEN
        RETURN 'Land';
    END IF;
    
    -- Check for penthouse
    IF unit_val ILIKE '%ph%' OR unit_val ILIKE '%penthouse%' THEN
        RETURN 'Penthouse';
    END IF;
    
    -- Default to apartment if it has a building and doesn't match above
    IF building_val IS NOT NULL AND building_val != '' THEN
        RETURN 'Apartment';
    END IF;
    
    -- Fallback
    RETURN 'Property';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Step 3: Create function to estimate bedrooms from unit number and size
CREATE OR REPLACE FUNCTION estimate_bedrooms(
    unit_val text,
    size_sqft_val numeric,
    property_type_val text
) RETURNS int AS $$
DECLARE
    unit_number text;
BEGIN
    -- Try to extract bedroom count from unit number patterns
    -- Common patterns: "201" (2BR), "301" (3BR), "1BR", "2BR", etc.
    
    -- Check if unit explicitly mentions BR
    IF unit_val ~* '(\d+)\s*br' THEN
        RETURN substring(unit_val FROM '(\d+)\s*br')::int;
    END IF;
    
    -- Check if unit explicitly mentions bed
    IF unit_val ~* '(\d+)\s*bed' THEN
        RETURN substring(unit_val FROM '(\d+)\s*bed')::int;
    END IF;
    
    -- Estimate based on size (rough approximation)
    IF size_sqft_val IS NOT NULL THEN
        -- Studio: < 600 sqft
        IF size_sqft_val < 600 THEN
            RETURN 0; -- Studio
        END IF;
        
        -- 1BR: 600-900 sqft
        IF size_sqft_val < 900 THEN
            RETURN 1;
        END IF;
        
        -- 2BR: 900-1400 sqft
        IF size_sqft_val < 1400 THEN
            RETURN 2;
        END IF;
        
        -- 3BR: 1400-2000 sqft
        IF size_sqft_val < 2000 THEN
            RETURN 3;
        END IF;
        
        -- 4BR: 2000-3000 sqft
        IF size_sqft_val < 3000 THEN
            RETURN 4;
        END IF;
        
        -- 5+ BR: > 3000 sqft
        IF size_sqft_val >= 3000 THEN
            RETURN 5;
        END IF;
    END IF;
    
    -- Default for villas and townhouses if no size info
    IF property_type_val IN ('Villa', 'Townhouse') THEN
        RETURN 3; -- Default assumption
    END IF;
    
    -- Default for apartments
    RETURN 2; -- Default assumption
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Step 4: Update existing properties with derived values
UPDATE properties
SET 
    property_type_derived = derive_property_type(unit, building, type, community, size_sqft),
    bedrooms_estimated = estimate_bedrooms(unit, size_sqft, property_type_derived)
WHERE property_type_derived IS NULL OR bedrooms_estimated IS NULL;

-- Step 5: Create indexes for faster filtering
CREATE INDEX IF NOT EXISTS idx_properties_type_derived ON properties(property_type_derived);
CREATE INDEX IF NOT EXISTS idx_properties_bedrooms_est ON properties(bedrooms_estimated);

-- Step 6: Create a view that combines actual and derived fields
CREATE OR REPLACE VIEW properties_enriched AS
SELECT 
    p.*,
    COALESCE(p.bedrooms, p.bedrooms_estimated) as bedrooms_final,
    COALESCE(p.type, p.property_type_derived) as property_type_final
FROM properties p;

-- Step 7: Update the search function to use derived fields
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
    owner_phone text,
    property_type text
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
        COALESCE(p.bedrooms, p.bedrooms_estimated) as bedrooms,
        p.size_sqft,
        COALESCE(p.last_price, t.price) as price_aed,
        COALESCE(t.buyer_name, o.norm_name, 'N/A') as owner_name,
        COALESCE(t.buyer_phone, o.norm_phone, 'N/A') as owner_phone,
        COALESCE(p.type, p.property_type_derived) as property_type
    FROM chunks c
    JOIN properties p ON p.id = c.property_id
    LEFT JOIN owners o ON o.id = p.owner_id
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
        AND (filter_bedrooms IS NULL OR COALESCE(p.bedrooms, p.bedrooms_estimated) = filter_bedrooms)
        AND (min_price IS NULL OR COALESCE(p.last_price, t.price) >= min_price)
        AND (max_price IS NULL OR COALESCE(p.last_price, t.price) <= max_price)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

COMMENT ON FUNCTION public.semantic_search_chunks IS 
'Semantic search with derived property types and bedroom estimates';

GRANT EXECUTE ON FUNCTION public.semantic_search_chunks TO anon, authenticated, service_role;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Derived fields added successfully!';
    RAISE NOTICE '📊 Properties now have:';
    RAISE NOTICE '   - property_type_derived (Villa/Apartment/Townhouse/etc.)';
    RAISE NOTICE '   - bedrooms_estimated (based on size and patterns)';
    RAISE NOTICE '';
    RAISE NOTICE '🔍 Search function updated to use these fields';
    RAISE NOTICE '⏳ Once embeddings finish generating, search will work!';
END $$;
