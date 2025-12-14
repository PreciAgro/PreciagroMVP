"""Prometheus metrics for conversational engine."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Info

from ..core.config import settings

chat_requests_total = Counter(
    "conversational_chat_requests_total",
    "Total chat requests processed",
    ["status"],
)

rag_used_total = Counter(
    "conversational_rag_used_total",
    "RAG usage count",
)

fallback_used_total = Counter(
    "conversational_fallback_used_total",
    "Responses that used deterministic fallback",
)

latency_histogram = Histogram(
    "conversational_latency_ms",
    "End-to-end latency per chat request (ms)",
    buckets=(50, 100, 200, 400, 800, 1600, 3200, 6400),
)

version_info = Info(
    "conversational_engine_version",
    "Version manifest for responses",
)
version_info.info(
    {
        "intent_schema": settings.intent_schema_version,
        "response_schema": settings.response_schema_version,
        "router": settings.router_version,
        "engine_api": settings.engine_api_version,
    }
)
