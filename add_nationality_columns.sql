-- Add nationality columns to transactions table
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS buyer_nationality TEXT,
ADD COLUMN IF NOT EXISTS seller_nationality TEXT;

-- Create index for faster nationality searches
CREATE INDEX IF NOT EXISTS idx_transactions_buyer_nationality ON transactions(buyer_nationality);
CREATE INDEX IF NOT EXISTS idx_transactions_seller_nationality ON transactions(seller_nationality);

-- Add comments for documentation
COMMENT ON COLUMN transactions.buyer_nationality IS 'Detected or inferred nationality of the buyer';
COMMENT ON COLUMN transactions.seller_nationality IS 'Detected or inferred nationality of the seller';
