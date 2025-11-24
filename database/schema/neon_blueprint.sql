-- ============================================================================
-- Neon Blueprint Schema for Dubai Real Estate Intelligence Platform
-- Builds on the Supabase structure with geospatial, ownership, lead tracking,
-- conversational linkage, and data lineage enhancements.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;

-- Extensions ----------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Enumerations --------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE owner_contact_type AS ENUM (
        'mobile', 'phone', 'email', 'whatsapp', 'telegram', 'wechat', 'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE owner_type AS ENUM (
        'person', 'company', 'government', 'developer', 'bank', 'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE completion_status AS ENUM ('ready', 'off_plan', 'under_construction', 'unknown');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE property_usage AS ENUM ('residential', 'commercial', 'mixed_use', 'hotel', 'industrial', 'unknown');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE lead_type AS ENUM ('seller', 'buyer', 'landlord', 'tenant', 'investor', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE lead_status AS ENUM ('new', 'contacted', 'qualified', 'hot', 'nurture', 'won', 'lost', 'inactive');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE lead_action_type AS ENUM ('call', 'email', 'whatsapp', 'meeting', 'note', 'demo', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE lead_action_outcome AS ENUM ('no_answer', 'interested', 'not_interested', 'follow_up', 'scheduled', 'closed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE property_event_type AS ENUM (
        'listed', 'price_change', 'sold', 'rented', 'off_market',
        'valuation_update', 'lead_created', 'campaign_touch', 'custom'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE data_source AS ENUM (
        'scraped_portal', 'dld', 'manual_agent', 'external_crm',
        'marketing_campaign', 'system_enrichment', 'unknown'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE conversation_intent AS ENUM (
        'valuation_request', 'prospecting', 'info_query', 'brochure_request',
        'follow_up', 'campaign', 'support', 'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Shared reference tables ---------------------------------------------------
CREATE TABLE IF NOT EXISTS agents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email text UNIQUE NOT NULL,
    full_name text,
    created_at timestamptz NOT NULL DEFAULT now(),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Geography hierarchy -------------------------------------------------------
CREATE TABLE IF NOT EXISTS communities (
    id bigserial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    slug text UNIQUE,
    region text,
    boundary_geom geometry(MultiPolygon, 4326),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS districts (
    id bigserial PRIMARY KEY,
    community_id bigint NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name text NOT NULL,
    slug text,
    boundary_geom geometry(MultiPolygon, 4326),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (community_id, name)
);

CREATE TABLE IF NOT EXISTS projects (
    id bigserial PRIMARY KEY,
    community_id bigint NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    district_id bigint REFERENCES districts(id) ON DELETE SET NULL,
    name text NOT NULL,
    slug text,
    developer text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (community_id, district_id, name)
);

CREATE TABLE IF NOT EXISTS clusters (
    id bigserial PRIMARY KEY,
    project_id bigint NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name text NOT NULL,
    description text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS buildings (
    id bigserial PRIMARY KEY,
    project_id bigint NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cluster_id bigint REFERENCES clusters(id) ON DELETE SET NULL,
    name text NOT NULL,
    tower_name text,
    completion completion_status DEFAULT 'unknown',
    geom geometry(Point, 4326),
    height_m numeric,
    floors integer,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS building_aliases (
    id bigserial PRIMARY KEY,
    building_id bigint NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    alias text NOT NULL,
    UNIQUE (building_id, alias)
);

-- Owners & contacts ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS owners (
    id bigserial PRIMARY KEY,
    external_owner_id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text NOT NULL,
    owner_type owner_type NOT NULL DEFAULT 'person',
    trade_license_no text,
    nationality text,
    is_absentee boolean,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (external_owner_id)
);

CREATE TABLE IF NOT EXISTS owner_contacts (
    id bigserial PRIMARY KEY,
    owner_id bigint NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    contact_type owner_contact_type NOT NULL DEFAULT 'mobile',
    value text NOT NULL,
    is_primary boolean NOT NULL DEFAULT false,
    verified_at timestamptz,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_id, contact_type, value)
);

CREATE TABLE IF NOT EXISTS property_owners (
    id bigserial PRIMARY KEY,
    property_id bigint NOT NULL,
    owner_id bigint NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    ownership_share numeric(5,2),
    is_primary boolean DEFAULT false,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (property_id, owner_id)
);

-- Properties ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS properties (
    id bigserial PRIMARY KEY,
    community_id bigint REFERENCES communities(id) ON DELETE SET NULL,
    district_id bigint REFERENCES districts(id) ON DELETE SET NULL,
    project_id bigint REFERENCES projects(id) ON DELETE SET NULL,
    cluster_id bigint REFERENCES clusters(id) ON DELETE SET NULL,
    building_id bigint REFERENCES buildings(id) ON DELETE SET NULL,
    unit_identifier text,
    property_number text,
    property_type text,
    usage property_usage DEFAULT 'unknown',
    sub_type text,
    completion completion_status DEFAULT 'unknown',
    bedrooms numeric,
    bathrooms numeric,
    floor_label text,
    status text DEFAULT 'owned',
    tenancy_status text,
    hold_years numeric,
    size_sqm numeric,
    size_sqft numeric,
    built_up_sqm numeric,
    built_up_sqft numeric,
    plot_size_sqm numeric,
    plot_size_sqft numeric,
    municipality_no text,
    municipality_sub_no text,
    land_number text,
    view text,
    geom geometry(Point, 4326),
    description_embedding vector(1536),
    embedding_model text,
    embedding_generated_at timestamptz,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (building_id, unit_identifier)
);

-- Transactions --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id bigserial PRIMARY KEY,
    property_id bigint REFERENCES properties(id) ON DELETE SET NULL,
    event_date date NOT NULL,
    price numeric,
    price_per_sqm numeric,
    price_per_sqft numeric,
    transaction_type text,
    completion completion_status DEFAULT 'unknown',
    property_type text,
    usage property_usage DEFAULT 'unknown',
    bedrooms numeric,
    bathrooms numeric,
    actual_size_sqm numeric,
    actual_size_sqft numeric,
    buyer_owner_id bigint REFERENCES owners(id) ON DELETE SET NULL,
    seller_owner_id bigint REFERENCES owners(id) ON DELETE SET NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Property events -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS property_events (
    id bigserial PRIMARY KEY,
    property_id bigint NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    event_type property_event_type NOT NULL,
    old_value jsonb,
    new_value jsonb,
    event_date timestamptz NOT NULL,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    created_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_property_events_property_date
    ON property_events (property_id, event_date DESC);

-- Leads & prospecting -------------------------------------------------------
CREATE TABLE IF NOT EXISTS leads (
    id bigserial PRIMARY KEY,
    owner_id bigint REFERENCES owners(id) ON DELETE SET NULL,
    property_id bigint REFERENCES properties(id) ON DELETE SET NULL,
    lead_type lead_type NOT NULL DEFAULT 'other',
    status lead_status NOT NULL DEFAULT 'new',
    source data_source DEFAULT 'unknown',
    assigned_agent_id uuid REFERENCES agents(id),
    score numeric(5,2),
    campaign_id text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    confidence numeric(5,2),
    verified_at timestamptz,
    verified_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lead_actions (
    id bigserial PRIMARY KEY,
    lead_id bigint NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    action_type lead_action_type NOT NULL,
    outcome lead_action_outcome,
    action_date timestamptz NOT NULL DEFAULT now(),
    notes text,
    agent_id uuid REFERENCES agents(id),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_lead_actions_lead_date
    ON lead_actions (lead_id, action_date DESC);

-- Conversations with data linkage ------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text,
    user_id text,
    assigned_agent_id uuid REFERENCES agents(id),
    intent conversation_intent,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    last_message_at timestamptz,
    last_message_preview text
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role text NOT NULL,
    content text NOT NULL,
    linked_property_id bigint REFERENCES properties(id) ON DELETE SET NULL,
    linked_owner_id bigint REFERENCES owners(id) ON DELETE SET NULL,
    linked_lead_id bigint REFERENCES leads(id) ON DELETE SET NULL,
    tool_calls jsonb,
    intent conversation_intent,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_created
    ON conversation_messages (conversation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_linked_objects
    ON conversation_messages (linked_property_id, linked_owner_id, linked_lead_id);

-- Embedding chunks ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunks (
    id bigserial PRIMARY KEY,
    property_id bigint NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    content text,
    embedding vector(1536),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    confidence numeric(5,2),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Data hygiene --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_quality_flags (
    id bigserial PRIMARY KEY,
    table_name text NOT NULL,
    record_id bigint NOT NULL,
    issue_type text NOT NULL,
    issue_details jsonb,
    resolved_at timestamptz,
    resolved_by uuid REFERENCES agents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES agents(id)
);

-- Indexing & performance ----------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_districts_geom ON districts USING gist (boundary_geom);
CREATE INDEX IF NOT EXISTS idx_communities_geom ON communities USING gist (boundary_geom);
CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_properties_geom ON properties USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_properties_filters
    ON properties (community_id, project_id, building_id, completion, usage, bedrooms, status);

CREATE INDEX IF NOT EXISTS idx_properties_price
    ON properties (size_sqft, built_up_sqft, plot_size_sqft);

CREATE INDEX IF NOT EXISTS idx_transactions_property_date
    ON transactions (property_id, event_date DESC);

CREATE INDEX IF NOT EXISTS idx_leads_status_agent
    ON leads (status, assigned_agent_id, lead_type);

CREATE INDEX IF NOT EXISTS idx_properties_embedding
    ON properties USING ivfflat (description_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- RAG-focused tables for document retrieval and chat context -----------------
CREATE TABLE IF NOT EXISTS rag_documents (
    id bigserial PRIMARY KEY,
    property_id bigint REFERENCES properties(id) ON DELETE CASCADE,
    title text NOT NULL,
    content text NOT NULL,
    embedding vector(1536),
    embedding_model text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source data_source DEFAULT 'unknown',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_property
    ON rag_documents (property_id);

CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding
    ON rag_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TABLE IF NOT EXISTS rag_prompt_templates (
    id bigserial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text,
    template text NOT NULL,
    required_fields text[] NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag_conversations (
    id bigserial PRIMARY KEY,
    property_id bigint REFERENCES properties(id) ON DELETE SET NULL,
    prompt_template_id bigint REFERENCES rag_prompt_templates(id) ON DELETE SET NULL,
    user_input text,
    assistant_response text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rag_conversations_property
    ON rag_conversations (property_id);

-- Views (examples) ----------------------------------------------------------
CREATE OR REPLACE VIEW v_multi_property_owners AS
SELECT
    o.id AS owner_id,
    o.name,
    COUNT(po.property_id) AS property_count,
    SUM(p.size_sqft) AS total_sqft,
    ARRAY_AGG(DISTINCT p.community_id) AS communities,
    MAX(p.updated_at) AS last_activity
FROM owners o
JOIN property_owners po ON po.owner_id = o.id
JOIN properties p ON p.id = po.property_id
GROUP BY o.id, o.name
HAVING COUNT(po.property_id) > 1;

CREATE OR REPLACE VIEW v_hot_leads AS
SELECT
    l.id,
    l.lead_type,
    l.status,
    l.score,
    l.assigned_agent_id,
    l.property_id,
    MAX(la.action_date) AS last_action_at
FROM leads l
LEFT JOIN lead_actions la ON la.lead_id = l.id
WHERE l.status IN ('hot', 'qualified')
GROUP BY l.id;

CREATE OR REPLACE VIEW v_chat_context AS
SELECT
    p.id AS property_id,
    c.name AS community_name,
    d.name AS district_name,
    pr.name AS project_name,
    b.name AS building_name,
    b.tower_name,
    b.completion AS building_completion,
    p.status AS property_status,
    p.property_type,
    p.usage,
    p.size_sqm,
    p.size_sqft,
    p.bedrooms,
    p.bathrooms,
    jsonb_build_object(
        'owner_id', owner_data.owner_id,
        'name', owner_data.owner_name,
        'nationality', owner_data.owner_nationality
    ) AS owner_info,
    jsonb_build_object(
        'date', latest_tx.event_date,
        'price', latest_tx.price,
        'season', latest_tx.completion,
        'usage', latest_tx.usage
    ) AS latest_transaction,
    jsonb_build_object(
        'project_source', pr.source,
        'building_tower', b.tower_name,
        'property_metadata', p.metadata
    ) AS metadata_context
FROM properties p
LEFT JOIN communities c ON p.community_id = c.id
LEFT JOIN districts d ON p.district_id = d.id
LEFT JOIN projects pr ON p.project_id = pr.id
LEFT JOIN buildings b ON p.building_id = b.id
LEFT JOIN LATERAL (
    SELECT o.id AS owner_id,
           o.name AS owner_name,
           o.nationality AS owner_nationality
    FROM property_owners po
    JOIN owners o ON o.id = po.owner_id
    WHERE po.property_id = p.id
    ORDER BY po.is_primary DESC NULLS LAST
    LIMIT 1
) owner_data ON true
LEFT JOIN LATERAL (
    SELECT t.event_date,
           t.price,
           t.completion,
           t.usage
    FROM transactions t
    WHERE t.property_id = p.id
    ORDER BY t.event_date DESC
    LIMIT 1
) latest_tx ON true;
