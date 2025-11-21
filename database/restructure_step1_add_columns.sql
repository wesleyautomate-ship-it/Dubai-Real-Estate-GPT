-- STEP 1: Add new columns only (fast operation)
-- Run this first in Supabase SQL Editor

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS master_community TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS sub_community TEXT;

ALTER TABLE properties ADD COLUMN IF NOT EXISTS master_community TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS sub_community TEXT;

-- Verify columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'transactions' 
  AND column_name IN ('master_community', 'sub_community');
