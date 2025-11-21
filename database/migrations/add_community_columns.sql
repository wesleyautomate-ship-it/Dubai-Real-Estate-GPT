-- Add master_community and sub_community columns
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS master_community TEXT,
ADD COLUMN IF NOT EXISTS sub_community TEXT;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_master_community ON transactions(master_community);
CREATE INDEX IF NOT EXISTS idx_transactions_sub_community ON transactions(sub_community);
