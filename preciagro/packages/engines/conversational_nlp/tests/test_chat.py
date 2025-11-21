"""Integration-style tests for conversational engine API with stubbed connectors."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from preciagro.packages.engines.conversational_nlp.app import app
from preciagro.packages.engines.conversational_nlp.app import orchestrator
from preciagro.packages.engines.conversational_nlp.core.config import settings
from preciagro.packages.engines.conversational_nlp.services.security import rate_limiter
from preciagro.packages.engines.conversational_nlp.services.rag import RAGRetriever


@pytest.fixture()
def client():
    """Yield a TestClient that runs startup/shutdown events."""
    with TestClient(app) as test_client:
        yield test_client


def _minimal_payload() -> dict[str, object]:
    return {
        "message_id": "msg-1",
        "session_id": "sess-1",
        "channel": "web",
        "user": {"id": "u1", "farm_ids": ["farm-1"], "role": "farmer"},
        "locale": "en-US",
        "text": "When should I plant maize?",
        "metadata": {"location": "Murewa"},
    }


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["engine"] == "conversational-nlp"
    assert body["status"] in {"ok", "degraded"}


def test_chat_message_returns_stubbed_answer(client):
    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "plan_planting"
    assert body["answer"]["text"]
    assert isinstance(body["tool_calls"], list)
    # With no AgroLLM or downstream URLs configured, we expect fallback and stub routes.
    assert body["fallback_used"] is True
    assert any(call["status"] in {"stubbed", "degraded", "no-tools"} for call in body["tool_calls"])


def test_chat_rejects_when_api_key_required(client):
    settings.inbound_api_key = "secret"
    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 401
    # Now include key
    resp = client.post("/chat/message", headers={"X-API-Key": "secret"}, json=_minimal_payload())
    assert resp.status_code == 200
    settings.inbound_api_key = ""  # reset


def test_rate_limit_blocks_after_threshold(client):
    # tighten limiter for test
    rate_limiter.limit = 1
    # First request ok
    ok = client.post("/chat/message", headers={"user_key": "u-test"}, json=_minimal_payload())
    assert ok.status_code == 200
    # Second should hit 429
    blocked = client.post("/chat/message", headers={"user_key": "u-test"}, json=_minimal_payload())
    assert blocked.status_code == 429
    # reset limiter
    rate_limiter.limit = settings.rate_limit_per_minute


def test_attachment_limits_and_types(client):
    payload = _minimal_payload()
    payload["attachments"] = [{"type": "image", "url": "https://example.com/img.jpg"} for _ in range(6)]
    resp = client.post("/chat/message", json=payload)
    assert resp.status_code == 413

    payload["attachments"] = [{"type": "video", "url": "https://example.com/vid.mp4"}]
    resp = client.post("/chat/message", json=payload)
    assert resp.status_code == 422


def test_rag_citations_returned_when_enabled(client):
    orchestrator.rag.enabled = True
    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["rag_used"] is True
    assert len(body["answer"].get("citations", [])) >= 1
    first_citation = body["answer"]["citations"][0]["id"]
    assert f"[{first_citation}]" in body["answer"]["text"]
    orchestrator.rag.enabled = False


def test_rag_uses_index_file_when_provided(tmp_path, client):
    index_file = tmp_path / "rag.json"
    custom_doc = [
        {
            "id": "custom_maize",
            "keywords": ["plan_planting", "maize", "custom"],
            "snippet": "Custom maize guidance.",
        }
    ]
    index_file.write_text(
        '[{"id":"custom_maize","keywords":["plan_planting","maize","custom"],"snippet":"Custom maize guidance."}]',
        encoding="utf-8",
    )
    retriever = RAGRetriever(enabled=True, top_k=1, index_path=str(index_file))
    orchestrator.rag = retriever

    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["rag_used"] is True
    assert body["answer"]["citations"][0]["id"] == "custom_maize"
    assert "[custom_maize]" in body["answer"]["text"]


def test_rejects_oversized_text(client):
    payload = _minimal_payload()
    payload["text"] = "a" * 12001
    resp = client.post("/chat/message", json=payload)
    assert resp.status_code == 413
