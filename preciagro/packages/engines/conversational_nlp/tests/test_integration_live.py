"""Optional live integration tests.

These are skipped unless real endpoints are configured via environment:
- AGROLLM_CLASSIFY_URL and AGROLLM_GENERATE_URL must be set (non-empty).
- QDRANT_HOST must not be ':memory:' if you want to assert RAG citations.
Run with: pytest -q preciagro/packages/engines/conversational_nlp/tests/test_integration_live.py
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from preciagro.packages.engines.conversational_nlp.app import app
from preciagro.packages.engines.conversational_nlp.core.config import settings


requires_live = pytest.mark.skipif(
    not (settings.agrollm_classify_url and settings.agrollm_generate_url),
    reason="Live AgroLLM endpoints not configured",
)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _payload() -> dict[str, object]:
    return {
        "message_id": "live-msg-1",
        "session_id": "live-sess-1",
        "channel": "web",
        "user": {"id": "live-user", "farm_ids": ["farm-1"], "role": "farmer"},
        "locale": "en-US",
        "text": "When should I plant maize in Murewa this year?",
        "metadata": {"location": "Murewa", "lat": -17.5, "lon": 31.2},
    }


@requires_live
def test_live_chat_with_agrollm(client):
    """Hits real AgroLLM endpoints; expects a 200 and sensible answer."""
    resp = client.post("/chat/message", json=_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] in {"plan_planting", "general_question", "check_weather"}
    assert body["answer"]["text"]
    if settings.rag_enabled and settings.qdrant_host != ":memory:":
        # When RAG is on and backed by a real index, citations should appear.
        assert body["rag_used"] is True
        assert body["answer"]["citations"]
        assert any(f"[{c['id']}]" in body["answer"]["text"] for c in body["answer"]["citations"])
