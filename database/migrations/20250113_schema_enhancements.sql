-- ============================================================================
-- Schema Enhancements for Relationships, Lookup Tables, and Analytics Support
-- Run this migration after existing base schema has been applied.
-- ============================================================================

BEGIN;

-- 1. Strengthen relationships ------------------------------------------------
ALTER TABLE properties
    DROP CONSTRAINT IF EXISTS properties_owner_id_fkey,
    ADD CONSTRAINT fk_properties_owner
        FOREIGN KEY (owner_id)
        REFERENCES owners(id)
        ON DELETE SET NULL;

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS owner_id BIGINT,
    DROP CONSTRAINT IF EXISTS transactions_owner_id_fkey,
    ADD CONSTRAINT fk_transactions_owner
        FOREIGN KEY (owner_id)
        REFERENCES owners(id)
        ON DELETE SET NULL;

ALTER TABLE chunks
    ALTER COLUMN property_id SET NOT NULL,
    DROP CONSTRAINT IF EXISTS chunks_property_id_fkey,
    ADD CONSTRAINT fk_chunks_property
        FOREIGN KEY (property_id)
        REFERENCES properties(id)
        ON DELETE CASCADE;

-- 2. Community / Building lookup tables -------------------------------------
CREATE TABLE IF NOT EXISTS communities (
    id BIGSERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    parent_id BIGINT REFERENCES communities(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS buildings (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    community_id BIGINT REFERENCES communities(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT buildings_name_community_key UNIQUE (name, community_id)
);

ALTER TABLE properties
    ADD COLUMN IF NOT EXISTS community_id BIGINT REFERENCES communities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS building_id BIGINT REFERENCES buildings(id) ON DELETE SET NULL,
    ADD CONSTRAINT IF NOT EXISTS properties_community_building_unit_key
        UNIQUE (community, building, unit);

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS community_id BIGINT REFERENCES communities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS building_id BIGINT REFERENCES buildings(id) ON DELETE SET NULL;

ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS community_id BIGINT REFERENCES communities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS building_id BIGINT REFERENCES buildings(id) ON DELETE SET NULL;

-- 3. Owner enrichment --------------------------------------------------------
CREATE TABLE IF NOT EXISTS owner_contacts (
    id BIGSERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    contact_type TEXT NOT NULL CHECK (contact_type IN ('phone','email','whatsapp','other')),
    value TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (owner_id, contact_type, value)
);

-- Ensure owners.nationality tracks nationalities table (added in prior migration)
ALTER TABLE owners
    ADD CONSTRAINT fk_owners_nationality
        FOREIGN KEY (nationality)
        REFERENCES nationalities(code)
        ON DELETE SET NULL;

-- 4. Transaction metadata ----------------------------------------------------
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS ingestion_batch_id UUID,
    ADD COLUMN IF NOT EXISTS data_confidence NUMERIC,
    ADD COLUMN IF NOT EXISTS alias_applied BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS phone_normalized BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS data_quality JSONB DEFAULT '{}'::jsonb;

-- 5. Property portfolio snapshot (materialized view) -------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS property_portfolio_snapshot AS
SELECT
    p.id AS property_id,
    p.owner_id,
    p.community,
    p.community_id,
    p.building,
    p.building_id,
    p.unit,
    p.type,
    p.status,
    p.size_sqft,
    p.last_price,
    p.last_transaction_date,
    CASE
        WHEN p.last_transaction_date IS NOT NULL THEN
            ROUND(EXTRACT(EPOCH FROM (CURRENT_DATE - p.last_transaction_date)) / 31536000, 2)
        ELSE NULL
    END AS hold_years
FROM properties p;

CREATE INDEX IF NOT EXISTS idx_property_portfolio_snapshot_owner
    ON property_portfolio_snapshot(owner_id);

CREATE INDEX IF NOT EXISTS idx_property_portfolio_snapshot_community
    ON property_portfolio_snapshot(community_id);

CREATE OR REPLACE FUNCTION refresh_property_portfolio_snapshot()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW property_portfolio_snapshot;
END;
$$;

-- 6. History tracking view ---------------------------------------------------
CREATE OR REPLACE VIEW property_events AS
SELECT
    t.id AS event_id,
    'transaction'::TEXT AS event_type,
    COALESCE(pr.id, NULL) AS property_id,
    COALESCE(pr.community, t.community) AS community,
    COALESCE(pr.building, t.building) AS building,
    COALESCE(pr.unit, t.unit) AS unit,
    t.transaction_date AS event_date,
    t.price,
    t.buyer_name,
    t.buyer_phone,
    t.seller_name,
    t.seller_phone,
    t.metadata,
    t.data_quality
FROM transactions t
LEFT JOIN properties pr
    ON pr.community = t.community
   AND pr.building = t.building
   AND pr.unit = t.unit;

-- 7. Indexing ---------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_transactions_community ON transactions(community);
CREATE INDEX IF NOT EXISTS idx_transactions_building ON transactions(building);
CREATE INDEX IF NOT EXISTS idx_transactions_unit ON transactions(unit);
CREATE INDEX IF NOT EXISTS idx_transactions_comm_bldg_unit ON transactions(community, building, unit);
CREATE INDEX IF NOT EXISTS idx_transactions_owner ON transactions(owner_id);

CREATE INDEX IF NOT EXISTS idx_properties_community ON properties(community);
CREATE INDEX IF NOT EXISTS idx_properties_building ON properties(building);
CREATE INDEX IF NOT EXISTS idx_properties_comm_bldg_unit ON properties(community, building, unit);
CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_id);

CREATE INDEX IF NOT EXISTS idx_owners_norm_phone ON owners(norm_phone);
CREATE INDEX IF NOT EXISTS idx_owner_contacts_owner_type ON owner_contacts(owner_id, contact_type);

-- 8. Embedding table hygiene -------------------------------------------------
ALTER TABLE chunks
    ALTER COLUMN chunk_type SET DEFAULT 'property_description',
    ALTER COLUMN chunk_type SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chunks_chunk_type ON chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_property ON chunks(property_id);
CREATE INDEX IF NOT EXISTS idx_chunks_community_building ON chunks(community_id, building_id);

COMMIT;
