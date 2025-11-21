# Supabase Connectivity Test

## Test Script
- Path: `scripts/test_supabase_connection.py`
- Command: `python scripts/test_supabase_connection.py`
- Purpose: Validate Supabase read/write access through the async REST client.

## Results
- **Read check**: Successfully fetched one record from `properties`.
- **Write check**: Inserted a synthetic owner record into `owners`, verified retrieval, then deleted it via the REST endpoint.
- **Cleanup**: Confirmed the temporary owner was removed (`Rows after delete: []`).
- **Outcome**: End-to-end CRUD flow succeeded with HTTP 200 responses where expected; no residual test data left behind.
