# Conversational / NLP Engine (MVP)

Intent-aware router in front of AgroLLM plus internal engines (GeoContext, Temporal Logic, Crop Intelligence, Image Analysis, Inventory) with optional RAG stubs.

## Run (local)
```bash
uvicorn preciagro.packages.engines.conversational_nlp.app:app --host 0.0.0.0 --port 8103 --reload
```

Environment knobs (see `core/config.py`):
- `AGROLLM_GENERATE_URL` / `AGROLLM_CLASSIFY_URL` / `AGROLLM_API_KEY`
- `GEO_CONTEXT_URL`, `TEMPORAL_LOGIC_URL`, `CROP_INTELLIGENCE_URL`, `INVENTORY_URL`, `IMAGE_ANALYSIS_URL`
- `REDIS_URL` (session cache), `RAG_ENABLED`, `RAG_TOP_K`
- `RAG_BACKEND` (default `qdrant`), `RAG_INDEX_PATH` (JSON index with `id`, `keywords`, `snippet`; defaults to built-in `data/rag_seed.json`)
- `QDRANT_HOST` (default `:memory:`), `QDRANT_PORT`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`
- `RAG_EMBEDDER_MODEL` (default `sentence-transformers/all-mpnet-base-v2`; set to `auto` or leave unset when using in-memory Qdrant to avoid downloads)
- `INTERNAL_API_KEY` (optional, sent as `X-API-Key` to downstream engines)
- `CONVERSATIONAL_API_KEY` (optional inbound auth for `/chat/message`)
- `RATE_LIMIT_PER_MINUTE` (per user/session key; defaults to 120)
- `ENGINE_RETRY_ATTEMPTS` / `ENGINE_RETRY_BACKOFF_SECONDS` (per-connector retry policy)
- Structured logs emitted per turn with intent, entities, tool calls, fallback/rag flags, and stage latencies.
- RAG uses Qdrant (in-memory by default) with sentence-transformers embeddings (`RAG_EMBEDDER_MODEL`, default `all-mpnet-base-v2`) and hashing fallback when unavailable; keyword/TF-IDF fallback remains if Qdrant is unreachable.

If URLs are not set, connectors return graceful stubs so the endpoint still responds.

## API
- `POST /chat/message` — channel-agnostic chat entry.
- `GET /health` — returns engine status.
- `/metrics` — Prometheus endpoint.

Example request:
```json
{
  "message_id": "example",
  "session_id": "sess-1",
  "channel": "web",
  "user": {"id": "u1", "farm_ids": ["farm-1"], "role": "farmer"},
  "locale": "en-US",
  "text": "When should I plant maize in Murewa this year?",
  "metadata": {"location": "Murewa", "lat": -17.5, "lon": 31.2}
}
```

Example response (stubbed connectors):
```json
{
  "intent": "plan_planting",
  "answer": {
    "text": "Plan to plant in your area during next 2-3 weeks...",
    "bullets": ["Use a medium-maturity hybrid suited to your rainfall zone."]
  },
  "tool_calls": [{"engine": "geo-context", "status": "stubbed"}],
  "fallback_used": true,
  "rag_used": false
}
```

## Tests
```bash
pytest preciagro/packages/engines/conversational_nlp/tests -q
```
Live integration (requires real endpoints configured):
```bash
AGROLLM_CLASSIFY_URL=... AGROLLM_GENERATE_URL=... QDRANT_HOST=... pytest preciagro/packages/engines/conversational_nlp/tests/test_integration_live.py -q
```

## RAG Ingestion (sample)
```bash
python scripts/ingest_rag_vector.py --index preciagro/packages/engines/conversational_nlp/data/rag_seed.json --host :memory: --collection conversational_rag
```
Set `QDRANT_HOST`/`PORT`/`API_KEY` to target a real Qdrant instance. Use `--embedder-model auto` (default) for in-memory dev (hashing); set to your sentence-transformer model when targeting a real service.
