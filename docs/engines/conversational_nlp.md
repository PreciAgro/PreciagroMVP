# Conversational / NLP Engine - Architecture & Build Plan

Single engine in front of AgroLLM and the rest of PreciAgro. It accepts text now (voice later), keeps farm + session context, classifies intent, routes to engines/tools, enriches with RAG, and returns grounded answers with guardrails.

## Scope and Goals
- Input: text from any channel (web, mobile, discreet chat app). Voice planned next.
- Understand farm-context intent and entities (crop, field/location, date/season, problem type, urgency).
- Route to internal engines/tools (Crop Intelligence, GeoContext, Temporal Logic, Inventory, Image Analysis, Agronomy RAG, etc.).
- Use AgroLLM for both intent classification and final response generation, with retrieval context when available.
- Maintain per-user conversation state (session, recent turns, farm metadata).

Non-goals (MVP):
- Full multilingual support (stick to English plus an optional single extra language if needed).
- Emotional support bot behavior; this is farm-assistance only.
- Direct autonomous actions (sprayer/drones) - defer to future Autonomous Action Engine.

## Recommended Stack and Infra
- Language/runtime: Python 3.11
- Framework: FastAPI (served by Uvicorn/Gunicorn)
- LLM: AgroLLM service wrapping strong open-source model (Llama/Qwen/DeepSeek/Mistral families) via HTTP or gRPC
- RAG: Qdrant/Weaviate/pgvector for vectors; Postgres or Mongo for doc metadata
- State: Redis for short-term conversation/session cache; Postgres for long-term logs and analytics
- Optional events: Kafka/NATS later for async engine fan-out and analytics
- Deployment: Docker; Azure/AWS (VM first, Kubernetes when scaling)

## API Surface (draft)
- `POST /chat/message` - text entry point (channel-agnostic). Auth via bearer token or API key.
- `POST /chat/voice` - later; accepts URL to audio or reference to uploaded blob.
- `GET /health` - readiness probe.

Request envelope (normalized by channel adapters):
```json
{
  "message_id": "uuid",
  "session_id": "uuid",
  "channel": "web|mobile|chat_app",
  "user": {"id": "u1", "farm_ids": ["f1"], "role": "farmer|agronomist|admin"},
  "locale": "en-US",
  "text": "When should I plant maize in Murewa this year?",
  "attachments": [{"type": "image", "url": "https://.../leaf.jpg"}],
  "metadata": {"device": "ios", "lat": -17.5, "lon": 31.2}
}
```

Response envelope:
```json
{
  "message_id": "uuid",
  "session_id": "uuid",
  "intent": "plan_planting",
  "entities": {"crop": "maize", "location": "Murewa", "season": "2025 main"},
  "answer": {
    "text": "Plant maize in Murewa between 15-30 Nov based on 45-55 mm forecasted rain...",
    "bullets": ["Check soil moisture before tillage", "Use medium-maturity hybrid", "Target 5.5 seeds/m^2"],
    "citations": [{"source": "rag", "id": "zim_maize_guide_p12"}]
  },
  "tool_calls": [
    {"engine": "geo-context", "status": "ok", "latency_ms": 210},
    {"engine": "temporal-logic", "status": "ok", "latency_ms": 95}
  ],
  "fallback_used": false,
  "rag_used": true,
  "latency_ms": 820
}
```

## Per-Turn Pipeline
1) Channel Adapter: Normalize payloads; do not hard-couple to WhatsApp or any single channel.
2) Session and Auth: Validate token/key, attach user/farm/role; fetch session state from Redis (recent N turns, current task).
3) Conversation Orchestrator: Turn management, handles multi-turn flows and interruptions.
4) NLU and Intent: AgroLLM prompt for JSON `{intent, entities, urgency}` plus light rules; validate with Pydantic schema and apply defaults on failure.
5) Tool and Engine Router: Map intent to engine connectors; fan-out with timeouts; degrade gracefully if a connector is slow or down.
6) RAG Retrieval: Build query from intent/entities; fetch top-K passages; mark when nothing useful is found.
7) LLM Response Generator: Prompt builder (system + user + tool outputs + RAG), guardrails (safety, regulatory constraints), streaming if available.
8) Response Formatter: Text, bullets, action steps; channel-specific formatting.
9) Logging and Feedback: Structured log per turn (user/farm, intent/entities, tools called, latencies, final response, feedback flag).

## Intent Schema v0 (versioned)
- Intents: `diagnose_disease`, `plan_planting`, `check_weather`, `inventory_status`, `general_question`, `market_prices`, `field_context`, `escalate_human`.
- Entities: `crop`, `location` (name plus lat/lon if present), `field_name`, `season_or_date`, `problem_type`, `urgency` (low/normal/high), `language` (optional).
- Contract: AgroLLM classifier returns strict JSON; validate and coerce to defaults (`general_question` plus empty entities) if invalid. Keep a `schema_version` field to allow future evolution.

Classifier prompt sketch:
- System: "You are classifying farm assistance intents. Reply with JSON only."
- Few-shot examples per intent.
- Instruction to avoid free text and to leave unknowns null.

## Tool and Engine Router
- Extensible registry: intent -> list of connector calls (with timeouts, required inputs, retry policy, aggregator).
- Example mappings:
  - `diagnose_disease`: if image present -> Image Analysis; then Crop Intelligence for likely diseases; optional KB lookup.
  - `plan_planting`: GeoContext (region/soil/rainfall), Temporal Logic (window), Crop Intelligence (varieties/densities).
  - `inventory_status`: Farm Inventory; optionally Temporal Logic for forecasted usage.
  - `check_weather`: GeoContext weather endpoint (or external weather adapter).
- Observability: log each connector call with status/latency; surface partial results with user-facing message when degraded.
- Connectors should share a standard response schema to avoid per-engine divergence.

## RAG Layer
- Collections: agronomy guides, chemical labels/regulations per region, PreciAgro FAQ/troubleshooting.
- Ingestion: chunk plus embed plus store in vector DB; metadata keyed by crop, region, growth stage, regulation scope.
- Retrieval: multi-field query derived from intent/entities; include top-K passages with source ids in prompt; if empty, set `rag_available=false` so AgroLLM avoids hallucinating.
- Tests: answers for rule-like questions must cite RAG context; ensure "I do not know" when no context.

## Prompting, Guardrails, Style
- System prompt: who the assistant is, safety boundaries, concise actionable style for farmers.
- Constraints: no invented prices, no illegal pesticide advice; say "I do not know" when uncertain or when context is missing.
- Temperature and max-tokens configurable per channel; prefer streaming responses.
- Response shaping: bullets plus short steps; highlight dates and numbers clearly.

## State, Storage, and Security
- Redis: session cache (recent turns, current task, last tool outputs).
- Postgres: conversation logs, analytics, user feedback, connector call summaries.
- Vector DB: RAG embeddings and metadata store.
- Auth: bearer token or API key; rate limit per user/app; redact PII in logs.
- Privacy: retention policy on conversation logs; consider anonymization for analytics exports.
- Internal auth between engines: optional `X-API-Key` header for downstream connectors.
- Inbound auth: optional `CONVERSATIONAL_API_KEY`; simple per-user rate limiting via `RATE_LIMIT_PER_MINUTE`.
- Observability: structured log per turn capturing intent, entities, tool calls, fallback/RAG flags, and stage latencies.
- RAG: Qdrant-backed retrieval by default (`RAG_BACKEND=qdrant`) with sentence-transformers embeddings (`RAG_EMBEDDER_MODEL`, default `all-mpnet-base-v2`) and hashing fallback; falls back to TF-IDF keyword retrieval if Qdrant unavailable.
- `RAG_INDEX_PATH`: optional JSON index (`id`, `keywords`, `snippet`) to override built-in seeds; ingestion script provided (`scripts/ingest_rag_vector.py`) targeting Qdrant or `:memory:` for local dev.
- Qdrant config: `QDRANT_HOST/PORT/API_KEY/COLLECTION`; default to `:memory:` for local runs.

## Observability and QA
- Metrics: overall latency, per-stage latency, connector error rates, intent distribution per week, RAG hit rate.
- Tracing: span per stage/tool call.
- Logging: structured JSON, redacting payloads over size thresholds.
- Evaluation: synthetic conversation scripts covering each intent plus degraded tool scenarios; regression set for RAG-cited answers.

## Build Plan (Phased)
- Phase 0 - Contracts and Infra: define API schemas (request/response/errors/versioning); define standard connector response schema; set repo skeleton, Docker base, Redis/Postgres/vector DB provisioning.
- Phase 1 - Bare Bones Chat: implement `/chat/message`, minimal Redis session, AgroLLM client with base prompt, plain Q&A (no tools or RAG), basic logging to Postgres and console; integration smoke test.
- Phase 2 - Intent and Router: classifier prompt plus schema validation; intent taxonomy finalized; router with fixed mappings; stubs/fakes for engines not ready; aggregation logic; weekly intent distribution metric (partial via structured logs).
- Phase 3 - RAG: current code ships a pluggable retrieval layer using built-in seeds or a JSON index (`RAG_INDEX_PATH`). Next step is real ingestion into a vector DB (e.g., pgvector/Qdrant) and enforcing citations in responses/tests.
- Phase 4 - Hardening: auth plus rate limiting, structured logging plus tracing, per-connector timeouts and graceful degradation, dashboard for latency/intent/error-rate, privacy review (what is stored, retention, anonymization plan).

## Open Questions / Next Decisions
- Pick default vector DB (pgvector vs Qdrant/Weaviate) and hosting plan.
- Choose default second language (if any) for MVP.
- Decide on streaming transport to clients (server-sent events vs websockets) for better UX.
- Define alignment with future Autonomous Action Engine for action recommendations vs execution.
