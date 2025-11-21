-- Restructure community columns to properly distinguish master communities from sub-communities
-- This fixes the issue where "community" column contains building names instead of master community

-- Step 1: Add new columns to both tables
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS master_community TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS sub_community TEXT;

ALTER TABLE properties ADD COLUMN IF NOT EXISTS master_community TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS sub_community TEXT;

-- Step 2: Move current "community" values to "sub_community"
UPDATE transactions SET sub_community = community WHERE sub_community IS NULL;
UPDATE properties SET sub_community = community WHERE sub_community IS NULL;

-- Step 3: Extract master community from source_file
-- Format: "Palm Jumeirah Jan 2025.xlsx" -> "Palm Jumeirah"
UPDATE transactions 
SET master_community = TRIM(REGEXP_REPLACE(source_file, '\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\.xlsx$', '', 'i'))
WHERE master_community IS NULL AND source_file IS NOT NULL;

-- For properties, we'll need to join with transactions to get the master community
-- Since properties don't have source_file, we match by unit+building
UPDATE properties p
SET master_community = (
    SELECT DISTINCT t.master_community
    FROM transactions t
    WHERE t.unit = p.unit 
      AND t.building = p.building
    LIMIT 1
)
WHERE p.master_community IS NULL;

-- Step 4: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_master_community ON transactions(master_community);
CREATE INDEX IF NOT EXISTS idx_transactions_sub_community ON transactions(sub_community);
CREATE INDEX IF NOT EXISTS idx_properties_master_community ON properties(master_community);
CREATE INDEX IF NOT EXISTS idx_properties_sub_community ON properties(sub_community);

-- Step 5: Add comments
COMMENT ON COLUMN transactions.master_community IS 'Master community name from source file (e.g., Palm Jumeirah, City Walk, Business Bay)';
COMMENT ON COLUMN transactions.sub_community IS 'Sub-community or building complex name (e.g., Serenia Residences, Balqis Residence)';
COMMENT ON COLUMN properties.master_community IS 'Master community name (e.g., Palm Jumeirah, City Walk, Business Bay)';
COMMENT ON COLUMN properties.sub_community IS 'Sub-community or building complex name (e.g., Serenia Residences, Balqis Residence)';

-- Step 6: Verification query
-- Run this to check the results:
-- SELECT source_file, master_community, sub_community, building FROM transactions LIMIT 20;
