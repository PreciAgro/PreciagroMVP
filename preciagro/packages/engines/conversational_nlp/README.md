# Conversational / NLP Engine (MVP)

Intent-aware router in front of AgroLLM plus internal engines (GeoContext, Temporal Logic, Crop Intelligence, Image Analysis, Inventory) with optional RAG stubs.

## Highlights
- **AgroLLM interface layer** (`services/agrollm_client.py`) with pluggable backends. The default `StubAgroLLMBackend` produces deterministic answers so `/chat/message` works locally without a real model. Switch to the HTTP backend by setting `AGROLLM_BACKEND=http` and providing real URLs/API keys.
- **Response builder + guardrails** (`services/response_builder.py`) builds structured prompts, merges tool + RAG context, enforces JSON output, and blocks unsafe instructions before returning a schema-compliant `AnswerPayload` with versions/error codes.
- **Tenant-aware auth + rate limiting** (`services/auth.py`, `services/security.py`) extract `tenant_id`, `farm_id`, `user_id`, and `user_role` from payloads/headers, enforce per-tenant/user limits, and propagate identity tags through logs and tool payloads.
- **Standard error & degradation contract** (`models.ErrorDetail`) covers upstream engine failures, attachment policy errors, degraded NLP fallbacks, and RAG gaps with explicit codes surfaced in responses/metrics/logs.
- **Session/Redis state** (`services/session.py`) maintains the last N turns, last tool outputs, and active intent per `session_id` with graceful in-memory fallback.
- **Router and connectors** (`services/router.py`) map intents to GeoContext, Temporal Logic, Crop Intelligence, Inventory, and Image Analysis clients with retries and stubbed responses when offline.
- **RAG layer** (`services/rag.py` + `rag_vector.py`) can run on a local TF-IDF index or an embedded Qdrant vector store; retrieval uses intent, entities, user text, and geo metadata.
- **Logging + persistence** – JSON logs, Prometheus metrics (`/metrics`), and JSONL conversation logging via `CONVERSATION_LOG_PATH`.

## Run locally
```bash
uvicorn preciagro.packages.engines.conversational_nlp.app:app --host 0.0.0.0 --port 8103 --reload
```
Or use `docker-compose.conversational.yml` to launch the API plus Redis (and optionally Qdrant).

Key environment knobs (see `core/config.py` / `.env.example`):
- API + schema versions: `ENGINE_API_VERSION`, `INTENT_SCHEMA_VERSION`, `RESPONSE_SCHEMA_VERSION`, `ROUTER_VERSION`
- Auth / limits: `CONVERSATIONAL_API_KEY`, `ADMIN_API_KEY`, `RATE_LIMIT_PER_MINUTE`, `TENANT_RATE_LIMIT_PER_MINUTE`
- Session/privacy: `SESSION_TTL_SECONDS`, `SESSION_RETENTION_HOURS`, `SESSION_HISTORY_TURNS`, `CONVERSATION_HISTORY_ENABLED`, `LOG_RETENTION_DAYS`, `ANONYMIZE_LOGS`
- Input policy: `MAX_MESSAGE_LENGTH`, `MAX_ATTACHMENTS`, `MAX_ATTACHMENT_BYTES`, `ALLOWED_ATTACHMENT_MIME_TYPES`
- Downstream engines: `GEO_CONTEXT_URL`, `TEMPORAL_LOGIC_URL`, `CROP_INTELLIGENCE_URL`, `INVENTORY_URL`, `IMAGE_ANALYSIS_URL`, `INTERNAL_API_KEY`
- RAG/vector: `FLAG_ENABLE_RAG`, `RAG_BACKEND`, `RAG_INDEX_PATH`, `QDRANT_HOST/PORT/API_KEY`, `RAG_EMBEDDER_MODEL`
- Feature flags: `FLAG_ENABLE_IMAGE_ENGINE`, `FLAG_ENABLE_TEMPORAL_ENGINE`, `FLAG_ENABLE_GEO_ENGINE`, `FLAG_FORCE_RULE_BASED_MODE`
- LLM: `AGROLLM_BACKEND`, `AGROLLM_CLASSIFY_URL`, `AGROLLM_GENERATE_URL`, `AGROLLM_API_KEY`, `CONVERSATION_SYSTEM_PROMPT`
- Observability: `CONVERSATION_LOG_PATH`, `LOG_RETENTION_DAYS`, `/metrics` exposes `conversational_engine_version`

If URLs are not set, connectors return graceful stubs and the AgroLLM stub keeps the pipeline working.

## API
- `POST /chat/message` – channel-agnostic chat entrypoint
- `GET /health` – reports engine status (degraded when running only with the stub backend)
- `/metrics` – Prometheus exporter

Example request:
```json
{
  "message_id": "example",
  "session_id": "sess-1",
  "channel": "web",
  "user": {
    "user_id": "u1",
    "tenant_id": "tenant-123",
    "farm_id": "farm-1",
    "farm_ids": ["farm-1"],
    "role": "farmer"
  },
  "locale": "en-US",
  "language_preference": "en-US",
  "text": "When should I plant maize in Murewa this year?",
  "metadata": {"location": "Murewa", "lat": -17.5, "lon": 31.2}
}
```

Example response (stubbed connectors + AgroLLM stub):
```json
{
  "intent": "plan_planting",
  "answer": {
    "summary": "Plan to plant in your area during mid-November.",
    "steps": [
      "Ensure soil moisture is adequate.",
      "Calibrate planter for uniform stands.",
      "Target planting window: mid-November."
    ],
    "warnings": ["Validate with local regulations."],
    "extras": {
      "session_history": [],
      "tool_outputs": {},
      "rag_snippets": [
        {"id": "zim_maize_window", "snippet": "For central Zimbabwe..."}
      ],
      "channel": "web",
      "feedback": null,
      "locale": "en-US"
    },
    "citations": [{"id": "zim_maize_window", "source": "rag"}],
    "status": "ok",
    "versions": {
      "intent_schema": "intent-v1",
      "response_schema": "response-v1",
      "router": "router-v1",
      "engine_api": "v1"
    },
    "errors": []
  },
  "errors": [],
  "tool_calls": [{"engine": "geo-context", "status": "stubbed"}],
  "fallback_used": false,
  "rag_used": true,
  "tenant_id": "tenant-123",
  "versions": {
    "intent_schema": "intent-v1",
    "response_schema": "response-v1",
    "router": "router-v1",
    "engine_api": "v1"
  }
}
```

## Tests
```bash
pytest preciagro/packages/engines/conversational_nlp/tests -q
```
- `tests/test_components.py` – unit coverage for intent extraction, router fan-out, AgroLLM stub, and RAG retrieval.
- `tests/test_chat.py` – API-level tests covering tenant extraction, feature flags, attachment policy, error codes, and RAG behaviors.
- `tests/test_integration_live.py` (opt-in) – hits live AgroLLM/vector endpoints when configured.

## RAG ingestion (sample)
```bash
python scripts/ingest_rag_vector.py \
  --index preciagro/packages/engines/conversational_nlp/data/rag_seed.json \
  --host :memory: \
  --collection conversational_rag
```
Set `QDRANT_HOST`/`PORT`/`API_KEY` to target a real Qdrant instance. Use `--embedder-model auto` (default) for in-memory dev; set to your sentence-transformer model when targeting a real service.

## Debugging & retention
- JSONL logs at `CONVERSATION_LOG_PATH` are scrubbed via `ANONYMIZE_LOGS` and truncated after `LOG_RETENTION_DAYS`. Use `python scripts/dump_conversation_turns.py -n 5 --log reports/conversation_turns.jsonl` to inspect the last N turns.
- `/admin/session/{session_id}?user_id=...` (requires `DEBUG_MODE=true` + admin API key) surfaces sanitized session state for troubleshooting.
