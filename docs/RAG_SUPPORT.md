# Retrieval-Augmented Generation (RAG) & Chat Support

This project already stores vector embeddings on `properties` and `chunks` within Neon, but the following schema extensions and documentation explicitly target chat applications that use RAG flows.

## Schema additions

- **`rag_documents`** keeps curated text objects (e.g., building descriptions, marketing blurbs, or aggregated transaction narratives) tied to a `property_id`. Each row stores an embedding vector plus metadata that can be refreshed independently of the original property row. Use this table when you want reusable, human-readable chunks beyond the raw Excel data.
- **`rag_prompt_templates`** version-controls templated prompts for agents. Store friendly names, required fields, and the template text (with interpolation placeholders such as `{community_name}`) so ingestion or UI layers can load them dynamically.
- **`rag_conversations`** tracks user & assistant exchanges plus the associated property ID and template. This allows you to replay or audit past chat sessions and to fine-tune prompt selection.
- **`v_chat_context`** synthesizes community, project, building, owner, and latest transaction metadata for every property. Use it as the base retrieval result before generating prompts without manually joining dozens of tables.

## RAG workflow

1. **Populate `rag_documents`.** After ingestion, break long property or transaction descriptions into semantic chunks, generate embeddings (e.g., via `backend/scripts/generate_embeddings.py`), and insert them into `rag_documents` along with `metadata` such as `{"source": "ingestion", "batch_id": "downtown-january"}`.
2. **Retrieve context for the chat.** Perform vector search on `rag_documents.embedding` and supplement it with `v_chat_context` rows so the agent understands the property’s canonical community, building, owner, and most recent transaction.
3. **Feed prompts from `rag_prompt_templates`.** Select a template by name (for example, `doctype:property_summary`) and interpolate fields like `{building_name}`, `{latest_transaction.price}`, or `{owner_info.name}` from the joined row.
4. **Record the conversation.** Insert the user prompt and response into `rag_conversations` so you can tune templates and retrievers over time.

## Example prompt template

```sql
INSERT INTO rag_prompt_templates (name, description, template, required_fields)
VALUES (
  'property_summary_chat',
  'Summarizes a Dubai property for chat',
  'You are a concierge for Dubai real estate. Summarize {building_name} in {community_name} (status: {property_status}, bedrooms: {bedrooms}). Latest sale: {latest_transaction.price} on {latest_transaction.date}. Include owner info from {owner_info.name}. Suggest one similar community nearby.',
  ARRAY['building_name', 'community_name', 'property_status', 'bedrooms', 'latest_transaction', 'owner_info']
);
```

## Conversation guidance

- Use `rag_prompt_templates` for deterministic prompt generation instead of hard-coded strings.
- Pair the template with the nearest neighbors from `rag_documents` to form the RAG context window and avoid hallucinations.
- Store `metadata` such as `{"retriever": "pgvector", "model": "gemini-2.0-flash"}` in `rag_conversations` so you can surface how a response was generated when reviewing transcripts.
