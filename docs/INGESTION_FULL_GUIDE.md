# End-to-End Ingestion & Embedding Guide (Neon + Gemini)

Use this checklist to load source files into Neon, populate every core table, and generate embeddings with Gemini (no OpenAI key required). It assumes the schema from `database/schema/neon_blueprint.sql` is applied (including `vector` extension).

## 1) Prerequisites
- `.env` set: `NEON_DB_URL`, `NEON_REST_URL`, `NEON_SERVICE_ROLE_KEY`, `GEMINI_API_KEY` (no OpenAI key needed when `LLM_PROVIDER=gemini`).
- Ensure `vector` extension exists: `SELECT extname FROM pg_extension WHERE extname='vector';`.
- Apply RAG tables if missing (run `database/schema/neon_blueprint.sql` or reuse the creation snippet in `backend/scripts` seeding script).
- Place source files in `.data_raw/` (e.g., `downtown latest data.xlsx`).

## 2) Sanity checks
- Verify the DB URL works (no channel_binding): `python - <<'PY' ... psycopg2.connect ... select 1 ... PY` or `psql` if installed.
- Optional: list expected tables: `\dt` (psql) or `SELECT table_name FROM information_schema.tables WHERE table_schema='public';`.

## 3) Run ingestion (structured tables)
- Command (small test): `python database/scripts/ingest_dubai_real_estate.py --files "downtown latest data" --max-rows 10`.
- Command (full file): `python database/scripts/ingest_dubai_real_estate.py --files "downtown latest data" --max-rows 0` (0 = all rows).
- Flags: `--skip-rows N` to skip headers/garbage; `--max-rows N` to limit for testing.
- The script fills: `communities`, `districts`, `projects`, `buildings`, `building_aliases`, `properties`, `owners`, `owner_contacts`, `transactions`. Clusters populate only if present in the source layout.
- If Gemini is enabled, alias enrichment runs inline; to skip it, temporarily unset `GEMINI_API_KEY`.

## 4) Generate embeddings with Gemini
The backend is configured to prefer Gemini (`models/text-embedding-004`) and pads to 1536 dims for compatibility.

- Property embeddings: `python backend/scripts/populate_property_embeddings.py`
- Chunk embeddings (RAG/search): `python backend/scripts/populate_chunks.py`
- Notes:
  - Ensure `LLM_PROVIDER=gemini` in `.env` and `GEMINI_API_KEY` is set.
  - These scripts read from Neon via `backend/neon_client.py`; no OpenAI key required.
  - Batching is per-script; expect slower runs than OpenAI—reduce scope if needed by limiting rows in the script or adding filters.

## 5) RAG documents (if you store curated text)
- Create/populate `rag_documents` with your content (marketing blurbs, summaries). Example insert:
  ```sql
  INSERT INTO rag_documents (property_id, title, content)
  VALUES (123, 'Property summary', 'Curated text...');
  ```
- Then run a Gemini embedding pass for RAG docs (adapt `populate_chunks` or a quick script using `embed_text`).

## 6) Optional seed data for leads/conversations
- To exercise those tables: insert a lead tied to a property, create a conversation, and add messages with `linked_property_id`/`linked_lead_id`. Keep PII minimal.

## 7) Post-ingestion validation
- Quick counts (example):
  ```sql
  SELECT 'properties' t, count(*) FROM properties
  UNION ALL SELECT 'transactions', count(*) FROM transactions
  UNION ALL SELECT 'owners', count(*) FROM owners
  UNION ALL SELECT 'owner_contacts', count(*) FROM owner_contacts
  UNION ALL SELECT 'buildings', count(*) FROM buildings
  UNION ALL SELECT 'building_aliases', count(*) FROM building_aliases
  UNION ALL SELECT 'chunks', count(*) FROM chunks
  UNION ALL SELECT 'rag_documents', count(*) FROM rag_documents;
  ```
- Spot-check recent inserts: `SELECT * FROM properties ORDER BY created_at DESC LIMIT 5;` and same for `transactions`.
- Confirm embeddings exist: `SELECT count(*) FROM properties WHERE description_embedding IS NOT NULL;` and `SELECT count(*) FROM chunks WHERE embedding IS NOT NULL;`.

## 8) Troubleshooting
- Connection timeouts: ensure VPN/firewall isn’t blocking TLS; remove `channel_binding=require` from URLs; keep `sslmode=require`.
- Gemini errors: check `GEMINI_API_KEY`, network egress, and model name (`models/text-embedding-004`). ALTS warnings on Windows are harmless.
- Slow runs: lower `--max-rows` during ingestion, and limit batches in embedding scripts.
- Missing tables (e.g., `rag_documents`): apply the schema file or run the creation DDL before embedding.

## 9) Minimal ingestion → embeddings workflow (Gemini-only)
1) `python database/scripts/ingest_dubai_real_estate.py --files "<file>" --max-rows 0`
2) `python backend/scripts/populate_property_embeddings.py`
3) `python backend/scripts/populate_chunks.py`
4) (Optional) insert rag_documents and embed them.
5) Validate counts and embedding presence as in step 7.
