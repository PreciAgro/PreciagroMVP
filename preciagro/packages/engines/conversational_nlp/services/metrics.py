"""Prometheus metrics for conversational engine."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

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
