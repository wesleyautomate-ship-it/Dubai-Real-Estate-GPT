# Schema & Feature Expansion Notes

These are the architectural upgrades we should layer on top of the current Dubai Real Estate schema once the Supabase connection is stable. The goal is to keep the chat assistant intelligent, contextual, and performant while also preparing the data for marketing/analytics use cases. Each section explains the schema pieces, the reason for them, and concrete ways the chat interface can use the new data.

## 1. Proper geospatial support

1. **Install PostGIS** (via Supabase SQL editor or a migration) so we can store and query spatial types and use all of PostgreSQL’s GIS functions from the backend.
2. **Columns**
   - Add `geometry(Point, 4326)` columns to `properties`, `buildings`, and any other object that should claim a location (parking pods, showrooms, agents).
   - Add `geometry(Polygon, 4326)` columns to `communities`, `districts`, and marketing zones/delivery areas once you have boundary data (import via GeoJSON or WKT).
3. **Indexes**
   - Create GIST indexes on every geometry column: `CREATE INDEX ON properties USING GIST(location)` etc. This lets PostGIS optimize distance, containment, and nearest-neighbor queries.
4. **Use cases**
   - “Show townhouses within a 15‑minute drive of Dubai Hills Mall” → compute a buffer around the mall point or travel-time polygon, then filter `properties` with `ST_DWithin`.
   - “Which buildings are inside both Business Bay and Downtown marketing zones?” → `ST_Intersects` across two polygons.
   - “List available 2BR units within 1km of the nearest metro station” → `ST_DWithin` against a `stations` table (or precomputed nearest station metadata).
   - “How many leads have been logged within the Dubai Hills Mall perimeter this week?” → attach spatial filters to `lead_actions`.
5. **Chat integration**
   - Have the backend tool add computed geography context (nearest district, metro, distance) to the chat response so the assistant can say “30 meters from Business Bay canal” without recomputing.
   - When generating narratives, present the bounding zone (“within the Dubai Hills catchment polygon”) to help analysts trust the spatial logic.

## 2. Clean ownership / parties model

1. **Tables**
   - `owners`: `id`, `owner_type` enum (`individual`, `company`), `name`, `trade_license_no`, `nationality`, `notes`, `metadata`, `source`, `confidence`, `verified_at`, `verified_by`.
   - `owner_contacts`: `owner_id` FK, `contact_type` enum (mobile/email/whatsapp/phone), `value`, `is_primary`, `verified_at`, `source`.
   - `property_owners`: connects `property_id` → `owner_id`, records `ownership_share` (optional percentage), `start_date`, `end_date`, `notes`, and `metadata` (to track joint ownership narrative).
2. **Why it matters**
   - Normalizes every party so you can query “owners in Dubai Hills with >2 properties” or “which leads link back to company X.”
   - Provides a single source of truth for contacts vs. buyers vs. seller leads.
   - Adds lineage metadata (`source`, `confidence`) so GPT can mention, “Ownership data from DLD (confidence 0.95).”
3. **Chat use cases**
   - “Show me all properties owned by this company and list the contact emails we have.”
   - “Highlight absentee owners with a Dubai Marina portfolio, and note which ones already have support tickets.”
   - “Who are the owners we have verified phone numbers for in Jumeirah Lakes Towers?”
4. **Integration**
   - Build backend tools that join `owners` + `property_owners` + `properties` to surface aggregated ownership stats, including contact metadata.
   - When a lead is created, automatically link it to `owner_id` if possible and stamp the lead with `owner_type` helpers so the chat can state “matched to company X.”

## 3. Property events/history

1. **Table structure**
   - `property_events`: `id`, `property_id`, `event_type` enum (`listed`, `price_change`, `sold`, `rented`, `off_market`, `valuation_update`, etc.), `old_value` JSONB, `new_value` JSONB, `event_date`, `source`, `created_by`, `metadata`, `confidence`.
2. **Purpose**
   - Builds a time-series record so you can reconstruct price velocity, listing behavior, and ownership transitions even if the current snapshot only stores the latest transaction.
   - Enables prompts that require delta logic (“prices dropped >10% in the last 6 months”).
3. **Examples**
   - “Prices dropped >10% over the last six months in this tower.” → filter `property_events` for `price_change` `new_value` vs `old_value`.
   - “Tell me the price and ownership history for unit 905.” → join events, transactions, and property owners.
   - “List owners whose rental revenue rose >15% year over year.” → detect `event_type = 'valuation_update'` or `rent_change`.
4. **Integration**
   - Generate views or RPCs that summarize recent event activity (`event_summary` per property).
   - When the assistant fetches property history, return both the `property_events` rows and a human-friendly narrative describing the change (value, source, confidence).
   - Capture `event_id` references inside tool metadata so you can answer follow-ups (“What evidence did you just cite?”).

## 4. Leads & prospecting layer

1. **Tables**
   - `leads`: `id`, `owner_id` (optional FK), `property_id` (side reference), `lead_type` enum (`seller`, `buyer`, `landlord`, `tenant`, `investor`), `source`, `status`, `assigned_agent_id`, `score`, `metadata`, `created_at`, `updated_at`.
   - `lead_actions`: `id`, `lead_id`, `action_type` (call, whatsapp, email, meeting, note), `outcome` (no_answer, interested, follow_up, closed_win, etc.), `action_date`, `notes`.
2. **Use cases**
   - “Give me my top 20 seller leads in Dubai Hills today, sorted by likelihood to list.”
   - “Summarize interactions with Mr. X and suggest the next follow-up step.”
   - “List leads tagged as ‘hot’ that have no action in the past 3 business days.”
3. **Chat integration**
   - Build chat tools that expose leads aggregations (per agent, status, geography).
   - Each conversation can produce lead/action entries by calling backend RPCs via tool-calling, so the assistant can auto-log “called the owner” actions.
4. **Data linking**
   - Keep `lead.metadata` referencing `owner_id`, `property_id`, or `conversation_id` so future prompts can join them (“Which chats are tied to hot leads?”).
   - Allow `lead_actions` to store `linked_conversation_id` if the chat agent triggers the action, enabling end-to-end provenance.

## 5. Conversation/Chat augmentation

1. **Enhance `conversation_messages`**
   - Add nullable `linked_property_id`, `linked_owner_id`, `linked_lead_id`.
   - Add `intent` enum (`ownership_request`, `history`, `valuation`, `prospecting`, `info_query`, `brochure_request`, etc.).
   - Add `tool_calls` JSONB that lists the tools/RPCs invoked along with timing metadata.
   - Add `confidence` or `resolved` flags so the UI can badge uncertain answers.
2. **Benefits**
   - Lets you filter chats with “price reduction” in Dubai Hills, “owner asked about selling,” or “leads without follow-up.”
   - Improves QA by surfacing tool latency and failure counts; the UI can warn customers when `tool_calls` include errors.
3. **Analysis**
   - Store created/updated timestamps per message so analytics can compute response latency or per-conversation throughput.
   - Capture `resolved_intent` from the tools so you can detect when the assistant escalated to manual workflows.

## 6. Data quality & lineage tags

1. **Uniform fields on fact tables**
   - Add `source` enum (`dld`, `portal`, `manual`, `crm`, `partner`, etc.), `confidence` (0‑100 or 0‑1), `verified_at`, `verified_by` to `properties`, `transactions`, `owners`, `property_events`, `leads`.
2. **Purpose**
   - Signals reliability so GPT can qualify responses (“This figure comes from DLD with 95% confidence”).
   - Enables auditing and alerting when low-confidence data is being surfaced.
3. **Implementation**
   - Either add columns directly or attach a `data_lineage` child table that stores `(table_name, column_name, source, confidence, verified_at, verified_by)`.
4. **Chat use cases**
   - Provide explanations such as “Built-up area is 1,840 sqft (high-confidence DLD). The listing portal says 1,950 sqft (lower confidence).”
   - Allow prompts like “Only show me high-confidence data from DLD or verified leads” by filtering on `confidence` + `source`.

## 7. Indexing & performance hygiene

1. **Indexes to add**
   - B-tree indexes on all FK columns (`community_id`, `project_id`, `building_id`, `owner_id`, `property_id`, `lead_id`, etc.).
   - B-tree or partial indexes on commonly filtered columns (`completion_status`, `property_type`, `usage`, `bedrooms`, `price`, `status`, `lead_status`).
   - GIN indexes on JSONB metadata fields frequently queried (e.g., `properties.metadata`, `leads.metadata`).
   - pgvector indexes (IVFFlat/HNSW) on the embedding vectors used for semantic search and `chat_embeddings`.
   - GIST indexes on geometry columns for spatial queries.
2. **Why**
   - Chat prompts often combine multiple filters (“2BRs in Marina priced 1–2M, high floor, marina view”), so indexes keep those composite scans fast.
   - Spatial + vector lookups become much faster with the right index types (GIST for geometry, HNSW/IVFFlat for vectors).
3. **Maintenance**
   - Run `ANALYZE`/`REINDEX` after bulk ingestion.
   - Monitor Supabase’s query statistics (via the dashboard) to ensure indexes are being used and add missing ones as needed.

## Next steps

1. Ensure connectivity to Supabase is healthy (resolve `402` errors) so the schema upgrades can be rolled out.
2. Prioritize migrations in the order above, starting with chat/ownership support, then events/history, and finally lead/prospecting + data quality fields.
3. Update the backend tools and chat prompts to leverage the new tables/indexes once they exist (e.g., `find_prospect_leads`, `summarize_property_events`, spatial filters).

Once those foundations are in place we can build a truly context-aware conversational assistant that understands geography, ownership, prospecting, and quality metadata end-to-end.
