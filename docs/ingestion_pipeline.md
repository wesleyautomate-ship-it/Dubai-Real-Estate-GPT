# Ingestion & Standardisation Overview

Latest update aligns the Excel/CSV ingestion flow with the analytics and GPT workflows.

## Key Enhancements
- Property upserts now return IDs which we attach to every transaction (stored as `property_id`) so downstream prompts can pivot directly to property detail records.
- Buyer and seller records are normalised and upserted into `owners`; buyer IDs are written back to transactions (`owner_id`) and the latest property snapshot, with additional owner IDs kept in `transaction.data_quality.buyer_owner_ids`.
- `master_community`, `sub_community`, and `price_per_sqft` are populated on both transactions and properties, giving GPT-ready context for CMAs and market reports.
- The script prints an analytics snapshot (transaction count, properties updated, unique communities/buildings/buyers) after each run for quick sanity checks.

## Run Sequence
1. Ensure `.data_raw` contains the latest source spreadsheets/CSVs.
2. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the environment (see `.env`).
3. Execute `python database/scripts/ingest_dubai_real_estate.py`.
4. Review the analytics snapshot output and Supabase tables (`transactions`, `properties`, `owners`) to confirm IDs and metrics populated as expected.
