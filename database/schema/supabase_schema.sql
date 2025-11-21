-- ============================================================================
-- Dubai Real Estate Schema (Hierarchical version)
-- Supports community → district → project → cluster → building → property
-- Designed for analytics + prospecting use cases
-- ============================================================================

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
SET search_path TO public;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- COMMUNITIES / DISTRICTS / PROJECTS / CLUSTERS / BUILDINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS communities (
  id               bigserial PRIMARY KEY,
  name             text NOT NULL UNIQUE,
  slug             text UNIQUE,
  region           text,
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS districts (
  id               bigserial PRIMARY KEY,
  community_id     bigint NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
  name             text NOT NULL,
  slug             text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (community_id, name)
);

CREATE TABLE IF NOT EXISTS projects (
  id               bigserial PRIMARY KEY,
  community_id     bigint NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
  district_id      bigint REFERENCES districts(id) ON DELETE SET NULL,
  name             text NOT NULL,
  slug             text,
  developer        text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (community_id, district_id, name)
);

CREATE TABLE IF NOT EXISTS clusters (
  id               bigserial PRIMARY KEY,
  project_id       bigint NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name             text NOT NULL,
  description      text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS buildings (
  id               bigserial PRIMARY KEY,
  project_id       bigint NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  cluster_id       bigint REFERENCES clusters(id) ON DELETE SET NULL,
  name             text NOT NULL,
  tower_name       text,
  completion_status text,
  latitude         numeric,
  longitude        numeric,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS building_aliases (
  id               bigserial PRIMARY KEY,
  building_id      bigint NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
  alias            text NOT NULL,
  UNIQUE (building_id, alias)
);

-- ============================================================================
-- OWNERS & OWNER CONTACTS
-- ============================================================================

CREATE TYPE owner_contact_type AS ENUM ('mobile', 'phone', 'email', 'other');
CREATE TYPE owner_type_enum AS ENUM ('individual', 'developer', 'bank', 'government', 'unknown');

CREATE TABLE IF NOT EXISTS owners (
  id                 bigserial PRIMARY KEY,
  external_owner_id  uuid NOT NULL DEFAULT gen_random_uuid(),
  raw_name           text,
  norm_name          text,
  norm_company       text,
  owner_type         owner_type_enum NOT NULL DEFAULT 'individual',
  nationality        text,
  metadata           jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (external_owner_id),
  UNIQUE (norm_name)
);

CREATE TABLE IF NOT EXISTS owner_contacts (
  id               bigserial PRIMARY KEY,
  owner_id         bigint NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
  contact_type     owner_contact_type NOT NULL DEFAULT 'mobile',
  value            text NOT NULL,
  is_primary       boolean NOT NULL DEFAULT false,
  verified_at      timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- ============================================================================
-- PROPERTIES
-- ============================================================================

CREATE TYPE completion_status AS ENUM ('ready', 'off-plan', 'under_construction', 'unknown');
CREATE TYPE property_usage AS ENUM ('residential', 'commercial', 'mixed_use', 'hotel', 'unknown');

CREATE TABLE IF NOT EXISTS properties (
  id                    bigserial PRIMARY KEY,
  community_id          bigint REFERENCES communities(id),
  district_id           bigint REFERENCES districts(id),
  project_id            bigint REFERENCES projects(id),
  cluster_id            bigint REFERENCES clusters(id),
  building_id           bigint REFERENCES buildings(id),
  master_community      text,
  community_name        text,
  sub_community_name    text,
  project_name          text,
  building_name         text,
  tower_name            text,
  unit_identifier       text,
  property_number       text,
  completion            completion_status DEFAULT 'unknown',
  property_type         text,
  usage                 property_usage DEFAULT 'unknown',
  sub_type              text,
  bedrooms              numeric,
  bedrooms_source       text,
  bedrooms_confidence   numeric,
  bathrooms             numeric,
  floor_label           text,
  status                text DEFAULT 'owned',
  owner_id              bigint REFERENCES owners(id) ON DELETE SET NULL,
  last_transaction_id   bigint,
  last_transaction_date date,
  purchase_price        numeric,
  hold_years            numeric,
  size_sqm              numeric,
  size_sqft             numeric,
  built_up_sqm          numeric,
  built_up_sqft         numeric,
  plot_size_sqm         numeric,
  plot_size_sqft        numeric,
  municipality_no       text,
  municipality_sub_no   text,
  land_number           text,
  unit_view             text,
  meta                  jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (building_id, unit_identifier)
);

-- ============================================================================
-- TRANSACTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS transactions (
  id                    bigserial PRIMARY KEY,
  property_id           bigint REFERENCES properties(id) ON DELETE SET NULL,
  community_id          bigint REFERENCES communities(id),
  district_id           bigint REFERENCES districts(id),
  project_id            bigint REFERENCES projects(id),
  building_id           bigint REFERENCES buildings(id),
  master_community      text,
  community_name        text,
  project_name          text,
  building_name         text,
  unit_identifier       text,
  transaction_date      date NOT NULL,
  price                 numeric,
  price_per_sqm         numeric,
  price_per_sqft        numeric,
  completion            completion_status DEFAULT 'unknown',
  property_type         text,
  usage                 property_usage DEFAULT 'unknown',
  sub_type              text,
  bedrooms              numeric,
  bathrooms             numeric,
  actual_size_sqm       numeric,
  actual_size_sqft      numeric,
  built_up_sqm          numeric,
  built_up_sqft         numeric,
  plot_size_sqm         numeric,
  plot_size_sqft        numeric,
  municipality_no       text,
  municipality_sub_no   text,
  land_number           text,
  buyer_owner_id        bigint REFERENCES owners(id) ON DELETE SET NULL,
  seller_name           text,
  buyer_name            text,
  buyer_phone           text,
  notes                 jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now()
);

-- ============================================================================
-- ALIASES / SEARCH HELPERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS aliases (
  id          bigserial PRIMARY KEY,
  alias       text NOT NULL,
  canonical   text NOT NULL,
  scope       text NOT NULL DEFAULT 'building', -- building/community/project
  confidence  numeric NOT NULL DEFAULT 0.5,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (alias, scope)
);

-- Embedding chunks (for semantic search)
CREATE TABLE IF NOT EXISTS chunks (
  id                bigserial PRIMARY KEY,
  property_id       bigint REFERENCES properties(id) ON DELETE CASCADE,
  content           text,
  embedding         vector(1536),
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- ============================================================================
-- ANALYTICS VIEWS / MATERIALIZED HELPERS (lightweight examples)
-- ============================================================================

CREATE OR REPLACE VIEW v_multi_property_owners AS
SELECT
  o.id AS owner_id,
  o.norm_name,
  COUNT(p.id) AS property_count,
  SUM(p.size_sqft) AS total_sqft,
  array_agg(DISTINCT p.community_name) AS communities
FROM owners o
JOIN properties p ON p.owner_id = o.id
GROUP BY o.id, o.norm_name
HAVING COUNT(p.id) > 1;

CREATE OR REPLACE VIEW v_property_hold_duration AS
SELECT
  p.id AS property_id,
  p.owner_id,
  p.master_community,
  p.building_name,
  p.unit_identifier,
  p.purchase_price,
  p.last_transaction_date,
  p.hold_years,
  CASE
    WHEN p.purchase_price > 0 AND p.size_sqft > 0 THEN p.purchase_price / p.size_sqft
    ELSE NULL
  END AS entry_price_per_sqft
FROM properties p;
