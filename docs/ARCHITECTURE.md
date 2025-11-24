# Architecture & Operation Guide

This project stitches together the ingestion pipeline, backend API, and frontend experience so you can hand the system a natural-language prompt, rely on Neon/Supabase for data, and get analytic or report-style responses.

## Core goals

1. **Normalize and store every Dubai property record** with consistent master community/project/building identifiers, owner details, and transaction snapshots (see `database/scripts/ingest_dubai_real_estate.py`).
2. **Surface the data via FastAPI + Supabase** so every endpoint (search, chat, owners, stats) can retrieve structured + semantic results.
3. **Power retrieval-augmented chat** with `properties.description_embedding`, `chunks`, and the `rag_*` tables/view described in `docs/RAG_SUPPORT.md`.

## Environment & setup

- Copy `.env.example` to `.env` and provide:
  - `NEON_DB_URL` (ingestion target)
  - `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (backend data access)
  - `GEMINI_API_KEY`/`OPENAI_API_KEY` + related model names (LLM enrichment/chat)
  - Optional metrics/tracing toggles for FastAPI (`METRICS_ENABLED`, `OTEL_*`).
- Install dependencies: `pip install -r backend/requirements.txt` and `cd frontend && npm install`.
- Run `scripts/test_full_flow.py` once to validate the Neon ingestion path, the Gemini key, and the backend command-line entry point.

## Ingestion pipeline

1. **File discovery:** `database/scripts/ingest_dubai_real_estate.py` scans `.data_raw/` for Excel/CSV exports matching `--files` arguments.
2. **Normalization:** layout-specific parsers (`parse_row_latest`, `transform_downtown_jan`, etc.) align each row to the canonical schema (master community, project, building, property, owner, transaction, usage flags).
3. **AI enrichment (optional):** `ai_enrichment.py` builds prompts with known communities/projects/buildings and calls `gemini_client.py` to get normalized entity matches plus alias suggestions. Fast failures on `API_KEY_INVALID` keep the rest of the pipeline intact.
4. **Neon persistence:** `NeonDB` caches communities/districts/projects, upserts buildings (with aliases filtered by `_existing_building_ids`), deduplicates owners, bulk upserts properties, and writes transactions before committing.
5. **Vector & RAG readiness:** After ingestion, run `backend/scripts/generate_embeddings.py` (or any embedding workflow) to populate `properties.description_embedding`, `chunks.embedding`, and the new `rag_documents` table so the chat layer has dense representations.

See `docs/ingestion_pipeline.md` for layout details and `database/schema/neon_blueprint.sql` for the target schema.

## Backend FastAPI service

- Entry point: `backend/main.py` wires authentication, rate limiting, tracing, metrics, and the Supabase client via `backend/supabase_client.py`.
- Routers live under `backend/api/`:
  - `search_api.py`: semantic search wrappers that call Supabase RPCs or `pgvector` queries.
  - `properties_api.py`, `owners_api.py`, `stats_api.py`: CRUD/stats for normalized entities.
  - `chat_endpoint.py` and `chat_tools_api.py`: orchestrate LLM prompts and tool usage using Gemini/OpenAI via `backend/llm_client.py`.
- Supabase is the authoritative source at runtime, so these APIs query `properties`, `chunks`, `transactions`, and (with the new doc) `rag_documents` + `v_chat_context` for richer context.

## Frontend React app

- Built with Vite in `frontend/`. Entry point: `frontend/src/main.jsx`.
- The UI displays search results, owner data, transactions, and the chat console. It hits `http://localhost:8787/api/*` by default (see Vite proxy config). Adjust `frontend/vite.config.js` if you run the backend on another port.
- Helper modules like `frontend/utils.js` format query-generated metrics, and the app refreshes embeddings/stats via `/api/stats` and `/api/search`.

## RAG & chat integration

- `docs/RAG_SUPPORT.md` explains how `rag_documents`, `rag_prompt_templates`, `rag_conversations`, and `v_chat_context` work together to supply a dense retrieval context plus templated prompts to Gemini/OpenAI.
- The backend’s chat routes combine these data sources with `backend/chat_endpoint.py`, allowing a prompt such as "summarize the latest CMA for Downtown Dubai" to rely on the canonical context view plus vectored chunks.

## Documentation map

- `docs/ARCHITECTURE.md` (**this page**)
- `docs/ingestion_pipeline.md` (parsing strategy)
- `docs/RAG_SUPPORT.md` (retrieval + chat tables) and `database/schema/neon_blueprint.sql`
- `docs/CHAT_AGENT_IMPLEMENTATION.md` (LLM/ tools/ prompts)
- `docs/PROJECT_STATUS.md` / `docs/IMPROVEMENTS_SUMMARY.md` for progress notes

## Cleanup notes

- Legacy quick-start files (`QUICKSTART.md`, `QUICK_START.md`) have been removed; `docs/ARCHITECTURE.md` now points you to the verified ingestion, backend, and frontend flow.
