# Dubai Real Estate Database

End-to-end system for turning raw Dubai property spreadsheets into normalized Postgres data that powers a semantic search + chat experience.

## Architecture snapshot
- **Ingestion:** `database/scripts/ingest_dubai_real_estate.py` parses Excel/CSV exports, normalizes rows, optionally enriches them with Gemini, and writes communities/projects/buildings/properties/transactions into Neon.
- **Backend:** `backend/main.py` starts FastAPI, wires Supabase `REST + RPC` clients, and exposes authenticated search, statistics, chat, and owner endpoints that drive the React UI and any programmatic clients.
- **Frontend:** The `frontend` directory contains a Vite + React SPA that proxies `/api/*` calls to the backend, renders semantic search results, and integrates with chat endpoints for report/analytics generation.
- **RAG/Chat support:** `docs/RAG_SUPPORT.md` documents how the schema (embeddings columns, `chunks`) plus the new `rag_*` tables and `v_chat_context` view fuel retrieval for natural-language analytics and CMA generation.

## Getting started (high-level)
1. Copy `.env.example` → `.env` and populate it with your Neon DB URL, Supabase credentials, GEMINI/OpenAI keys, and API settings.
2. Install Python dependencies: `pip install -r backend/requirements.txt` (optionally create a virtual env).
3. Install the frontend toolchain: `cd frontend && npm install`.
4. Load an Excel export with `python database/scripts/ingest_dubai_real_estate.py --files "downtown latest data" --max-rows 500` (remove `--max-rows` for full runs).
5. Start the backend: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8787`.
6. Run the frontend dev server: `cd frontend && npm run dev` (it proxies `/api` to the backend).
7. For verification, `scripts/test_full_flow.py` exercises the database, Gemini, and ingestion script; run it once you have `.env` in place.

For full, step-by-step instructions see `docs/ARCHITECTURE.md`.

## Directory overview
- `database/`: ingestion scripts, normalization helpers, Neon DB helpers, and schema definitions.
- `backend/`: FastAPI code (routers in `backend/api/`), Supabase client, authentication middleware, and logging config.
- `frontend/`: Vite + React UI that surfaces search, chat, aliases, and analytics.
- `docs/`: onboarding/architecture guidance, ingestion walkthroughs, and RAG/chat playbooks.
- `scripts/`: utility scripts such as `test_full_flow` and analytics helpers.

## Documentation worth bookmarking
- `docs/ARCHITECTURE.md`: high-level system design, data flow, and the backend↔frontend contract.
- `docs/ingestion_pipeline.md`: detailed breakdown of how each Excel layout is normalized and written to Neon.
- `docs/RAG_SUPPORT.md`: how embeddings, prompt templates, and conversation logging support semantic retrieval and report generation.
- `docs/CHAT_AGENT_IMPLEMENTATION.md`: deep dive into the chat agents, tool definitions, and how prompts are orchestrated.
- `database/schema/neon_blueprint.sql`: the production schema, including `rag_*` tables and indexing for pgvector queries.

## Clean slate
- Legacy quick-start helpers have been replaced with the structured documentation above. If you are unsure where to begin, start with `docs/ARCHITECTURE.md` and `docs/ingestion_pipeline.md`.
