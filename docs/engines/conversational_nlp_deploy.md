# Conversational/NLP Engine - Deployment Notes

## Docker
Build and run:
```bash
docker build -f preciagro/packages/engines/conversational_nlp/Dockerfile -t conversational-nlp .
docker run -p 8103:8103 --env-file .env conversational-nlp
```

Key env vars: see `.env.example` in repo for all knobs (AgroLLM, Qdrant, downstream engines, auth/rate limits, retries, OTLP).

Health: `/health`  
Metrics: `/metrics`

## Prometheus / Grafana
- Scrape `/metrics` from the service.
- Useful panels: `conversational_latency_ms` (p50/p95), `conversational_chat_requests_total{status}`, `conversational_rag_used_total`, `conversational_fallback_used_total`.

## Tracing (OTLP)
Set:
```
OTEL_EXPORTER_OTLP_ENDPOINT=http://<collector>:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_SERVICE_NAME=conversational-nlp
```
Spans cover: intent_classify, router_call, rag_retrieve, llm_generate, connector_*.

## Rate Limits / Auth
- Enable `CONVERSATIONAL_API_KEY` outside dev.
- Tune `RATE_LIMIT_PER_MINUTE` per user/session key.

## RAG Ingestion
```bash
python scripts/ingest_rag_vector.py --index <docs.json> --host <qdrant-host> --port <port> --api-key <key> --collection conversational_rag --embedder-model <model|auto>
```
Docs JSON: `[{ "id": "doc1", "snippet": "...", "keywords": ["maize","planting"] }]`.

## Load Test (lightweight)
```bash
CHAT_URL=http://<host>:8103/chat/message python scripts/load_test_chat.py
```

## Docker Compose
```bash
docker compose -f docker-compose.conversational.yml up --build
```

## Attachment / Request Limits
- Text max length: 12k chars
- Max attachments: 5; types allowed: image, document; URL required
- Oversized/invalid requests return 413/422.

## Grafana (example panels)
- Latency histogram: `histogram_quantile(0.95, sum(rate(conversational_latency_ms_bucket[5m])) by (le))`
- Error rate: `sum(rate(conversational_chat_requests_total{status!="ok"}[5m]))`
- RAG hit rate: `sum(rate(conversational_rag_used_total[5m]))`
- Fallback rate: `sum(rate(conversational_fallback_used_total[5m]))`
