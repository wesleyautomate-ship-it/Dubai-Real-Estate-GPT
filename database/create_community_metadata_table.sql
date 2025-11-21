-- Create community_metadata table
-- This table stores rich information about Dubai communities for enhanced search and recommendations

CREATE TABLE IF NOT EXISTS community_metadata (
    id SERIAL PRIMARY KEY,
    community TEXT NOT NULL UNIQUE,
    type TEXT,  -- e.g., "Luxury", "Mid-market", "Affordable"
    sub_clusters TEXT,
    property_types TEXT,
    bedroom_range TEXT,
    avg_price_sale TEXT,
    avg_rent TEXT,
    rental_yield TEXT,
    service_charge TEXT,
    demographics TEXT,
    nearby_infra TEXT,
    developer TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on community name for fast lookups
CREATE INDEX IF NOT EXISTS idx_community_metadata_community ON community_metadata(community);

-- Create index on type for filtering
CREATE INDEX IF NOT EXISTS idx_community_metadata_type ON community_metadata(type);

-- Add comment
COMMENT ON TABLE community_metadata IS 'Comprehensive metadata about Dubai communities including pricing, demographics, and infrastructure';

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_community_metadata_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_update_community_metadata_updated_at ON community_metadata;
CREATE TRIGGER trigger_update_community_metadata_updated_at
    BEFORE UPDATE ON community_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_community_metadata_updated_at();
