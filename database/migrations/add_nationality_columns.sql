-- Migration: Add nationality tracking to Dubai Real Estate Database
-- Created: 2025-01-12
-- Description: Adds nationality columns to transactions and owners tables for filtering

-- Step 1: Create nationalities reference table
CREATE TABLE IF NOT EXISTS nationalities (
  id SERIAL PRIMARY KEY,
  code VARCHAR(3) UNIQUE NOT NULL,  -- ISO 3166-1 alpha-3 code (e.g., 'UAE', 'IND', 'GBR')
  name TEXT NOT NULL,                -- Full name (e.g., 'United Arab Emirates', 'India', 'United Kingdom')
  region TEXT,                       -- Region (e.g., 'Middle East', 'South Asia', 'Europe')
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 2: Add nationality columns to transactions table
ALTER TABLE transactions 
  ADD COLUMN IF NOT EXISTS seller_nationality VARCHAR(3) REFERENCES nationalities(code),
  ADD COLUMN IF NOT EXISTS buyer_nationality VARCHAR(3) REFERENCES nationalities(code);

-- Step 3: Add nationality column to owners table
ALTER TABLE owners
  ADD COLUMN IF NOT EXISTS nationality VARCHAR(3) REFERENCES nationalities(code);

-- Step 4: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_buyer_nationality ON transactions(buyer_nationality);
CREATE INDEX IF NOT EXISTS idx_transactions_seller_nationality ON transactions(seller_nationality);
CREATE INDEX IF NOT EXISTS idx_owners_nationality ON owners(nationality);

-- Step 5: Insert common nationalities in Dubai real estate market
INSERT INTO nationalities (code, name, region) VALUES
  -- GCC Countries
  ('UAE', 'United Arab Emirates', 'Middle East'),
  ('SAU', 'Saudi Arabia', 'Middle East'),
  ('QAT', 'Qatar', 'Middle East'),
  ('KWT', 'Kuwait', 'Middle East'),
  ('OMN', 'Oman', 'Middle East'),
  ('BHR', 'Bahrain', 'Middle East'),
  
  -- Major Middle East
  ('EGY', 'Egypt', 'Middle East'),
  ('LBN', 'Lebanon', 'Middle East'),
  ('JOR', 'Jordan', 'Middle East'),
  ('SYR', 'Syria', 'Middle East'),
  ('IRQ', 'Iraq', 'Middle East'),
  ('IRN', 'Iran', 'Middle East'),
  
  -- South Asia
  ('IND', 'India', 'South Asia'),
  ('PAK', 'Pakistan', 'South Asia'),
  ('BGD', 'Bangladesh', 'South Asia'),
  ('LKA', 'Sri Lanka', 'South Asia'),
  ('NPL', 'Nepal', 'South Asia'),
  ('AFG', 'Afghanistan', 'South Asia'),
  
  -- Europe
  ('GBR', 'United Kingdom', 'Europe'),
  ('FRA', 'France', 'Europe'),
  ('DEU', 'Germany', 'Europe'),
  ('ITA', 'Italy', 'Europe'),
  ('ESP', 'Spain', 'Europe'),
  ('RUS', 'Russia', 'Europe'),
  ('NLD', 'Netherlands', 'Europe'),
  ('BEL', 'Belgium', 'Europe'),
  ('CHE', 'Switzerland', 'Europe'),
  ('AUT', 'Austria', 'Europe'),
  ('SWE', 'Sweden', 'Europe'),
  ('NOR', 'Norway', 'Europe'),
  ('DNK', 'Denmark', 'Europe'),
  ('IRL', 'Ireland', 'Europe'),
  ('POL', 'Poland', 'Europe'),
  ('ROU', 'Romania', 'Europe'),
  
  -- East Asia
  ('CHN', 'China', 'East Asia'),
  ('JPN', 'Japan', 'East Asia'),
  ('KOR', 'South Korea', 'East Asia'),
  ('HKG', 'Hong Kong', 'East Asia'),
  ('SGP', 'Singapore', 'East Asia'),
  
  -- Southeast Asia
  ('PHL', 'Philippines', 'Southeast Asia'),
  ('THA', 'Thailand', 'Southeast Asia'),
  ('MYS', 'Malaysia', 'Southeast Asia'),
  ('IDN', 'Indonesia', 'Southeast Asia'),
  ('VNM', 'Vietnam', 'Southeast Asia'),
  
  -- North America
  ('USA', 'United States', 'North America'),
  ('CAN', 'Canada', 'North America'),
  ('MEX', 'Mexico', 'North America'),
  
  -- Oceania
  ('AUS', 'Australia', 'Oceania'),
  ('NZL', 'New Zealand', 'Oceania'),
  
  -- Africa
  ('ZAF', 'South Africa', 'Africa'),
  ('NGA', 'Nigeria', 'Africa'),
  ('KEN', 'Kenya', 'Africa'),
  ('ETH', 'Ethiopia', 'Africa'),
  ('MAR', 'Morocco', 'Africa'),
  
  -- South America
  ('BRA', 'Brazil', 'South America'),
  ('ARG', 'Argentina', 'South America'),
  ('CHL', 'Chile', 'South America'),
  
  -- Other
  ('TUR', 'Turkey', 'Middle East'),
  ('ISR', 'Israel', 'Middle East')
ON CONFLICT (code) DO NOTHING;

-- Step 6: Update v_current_owner view to include nationality
CREATE OR REPLACE VIEW v_current_owner AS
SELECT DISTINCT ON (community, building, unit)
  community, 
  building, 
  unit,
  buyer_name AS owner_name,
  buyer_phone AS owner_phone,
  buyer_nationality AS owner_nationality,
  price AS last_price,
  transaction_date AS last_transfer_date
FROM transactions
WHERE buyer_name IS NOT NULL
ORDER BY community, building, unit, transaction_date DESC;

-- Step 7: Create helper view for nationality statistics
CREATE OR REPLACE VIEW v_nationality_stats AS
SELECT 
  n.code,
  n.name,
  n.region,
  COUNT(DISTINCT t.buyer_name) AS owner_count,
  COUNT(*) AS transaction_count,
  SUM(t.price) AS total_value,
  AVG(t.price) AS avg_price
FROM nationalities n
LEFT JOIN transactions t ON t.buyer_nationality = n.code
GROUP BY n.code, n.name, n.region
ORDER BY transaction_count DESC;

-- Step 8: Create function to search owners by nationality
CREATE OR REPLACE FUNCTION search_by_nationality(
  nationality_code VARCHAR(3),
  limit_count INT DEFAULT 100
)
RETURNS TABLE (
  community TEXT,
  building TEXT,
  unit TEXT,
  owner_name TEXT,
  owner_phone TEXT,
  nationality VARCHAR(3),
  last_price NUMERIC,
  last_transfer_date DATE
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    v.community,
    v.building,
    v.unit,
    v.owner_name,
    v.owner_phone,
    v.owner_nationality,
    v.last_price,
    v.last_transfer_date
  FROM v_current_owner v
  WHERE v.owner_nationality = nationality_code
  ORDER BY v.last_transfer_date DESC
  LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE nationalities IS 'Reference table for owner nationalities';
COMMENT ON COLUMN transactions.buyer_nationality IS 'Nationality of property buyer (ISO 3166-1 alpha-3 code)';
COMMENT ON COLUMN transactions.seller_nationality IS 'Nationality of property seller (ISO 3166-1 alpha-3 code)';
COMMENT ON COLUMN owners.nationality IS 'Nationality of property owner (ISO 3166-1 alpha-3 code)';
COMMENT ON FUNCTION search_by_nationality IS 'Search current property owners by nationality code';
