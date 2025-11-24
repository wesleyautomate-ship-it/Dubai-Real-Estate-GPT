# RealEstateGPT Iteration Plan

Downtown-only test data; single user; optimize for fast iteration. Update this checklist as tasks complete.

## 1) Stability & Resilience
- [x] Add reusable error banner component; surface API failures per card.
- [x] Apply skeleton/loading states to all result cards (ownership/history/search/portfolio/analytics).
- [x] Handle empty stats gracefully (show "Downtown test data" instead of broken zero state).
- [x] Add short timeouts on Supabase RPCs and HTTP calls.

## 2) Provider Control & Parity
- [x] Chat endpoints accept `provider` param (per-request) and pass to `get_llm_client` end-to-end (chat API exposed with provider/meta).
- [x] Hide Gemini option if `GEMINI_API_KEY` missing; keep model dropdown functional.
- [x] Return `request_id`, provider, and latency in chat responses; log same server-side.

## 3) Observability
- [x] Server: log tool-call timings, RPC latency, and request id; tag with provider and intent.
- [x] Client: console logs for request id, provider, latency, result counts, errors.

## 4) Performance
- [x] Cache alias map client-side (fetch once per session).
- [x] Debounce semantic search requests in UI (basic rapid-submit guard + cache for repeated queries).
- [x] Add backend RPC timeouts and sensible retry/fallback for critical calls.

## 5) Types & Structure
- [x] Introduce TypeScript interfaces for API payloads/responses to prevent schema drift. (added types.d.ts)
- [x] Refactor frontend into ConversationController + ResultCards to prep for streaming. (cards modularized)

## 6) Feature Expansion (post-stability)
- [x] CMA / light valuation: wrap `find_comparables` RPC into a CMA card (subject vs comps, avg psf, estimated range).
- [x] Alerts: save query + notify on new transactions in a community/building (prototype/in-memory).
- [x] Portfolio hygiene: flag ambiguous owners (same phone across multiple names) and surface "needs verification" tasks.

## Order of Execution
1. Stability & Resilience
2. Provider Control & Parity
3. Observability
4. Performance
5. Types & Structure
6. Feature Expansion
