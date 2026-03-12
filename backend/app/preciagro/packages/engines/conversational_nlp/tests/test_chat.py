"""Integration-style tests for conversational engine API with stubbed connectors."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from preciagro.packages.engines.conversational_nlp.app import app, orchestrator
from preciagro.packages.engines.conversational_nlp.core.config import settings
from preciagro.packages.engines.conversational_nlp.services.rag import RAGRetriever
from preciagro.packages.engines.conversational_nlp.services.security import rate_limiter


@pytest.fixture()
def client():
    """Yield a TestClient that runs startup/shutdown events."""
    original_api_key = settings.inbound_api_key
    original_user_limit = rate_limiter.user_limit
    original_tenant_limit = rate_limiter.tenant_limit
    settings.inbound_api_key = ""
    rate_limiter.user_limit = settings.rate_limit_per_minute
    rate_limiter.tenant_limit = settings.tenant_rate_limit_per_minute
    rate_limiter.buckets.clear()
    with TestClient(app) as test_client:
        yield test_client
    settings.inbound_api_key = original_api_key
    rate_limiter.user_limit = original_user_limit
    rate_limiter.tenant_limit = original_tenant_limit
    rate_limiter.buckets.clear()


def _minimal_payload() -> dict[str, object]:
    return {
        "message_id": "msg-1",
        "session_id": "sess-1",
        "channel": "web",
        "user": {
            "user_id": "u1",
            "tenant_id": "tenant-1",
            "farm_id": "farm-1",
            "farm_ids": ["farm-1"],
            "role": "farmer",
        },
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
    assert "versions" in body


def test_chat_message_returns_structured_answer(client):
    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "plan_planting"
    assert body["answer"]["summary"]
    assert isinstance(body["answer"]["steps"], list)
    assert body["answer"]["status"] in {"ok", "degraded"}
    assert body["answer"]["versions"]["intent_schema"] == settings.intent_schema_version
    assert any(
        call["status"] in {"stubbed", "degraded", "disabled", "no-tools"}
        for call in body["tool_calls"]
    )


def test_chat_rejects_when_api_key_required(client):
    settings.inbound_api_key = "secret"
    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 401
    resp = client.post("/chat/message", headers={"X-API-Key": "secret"}, json=_minimal_payload())
    assert resp.status_code == 200
    settings.inbound_api_key = ""


def test_rate_limit_blocks_after_threshold(client):
    rate_limiter.user_limit = 1
    rate_limiter.tenant_limit = 10
    rate_limiter.buckets.clear()
    ok = client.post("/chat/message", json=_minimal_payload())
    assert ok.status_code == 200
    blocked = client.post("/chat/message", json=_minimal_payload())
    assert blocked.status_code == 429
    detail = blocked.json()
    assert detail["detail"]["errors"][0]["code"] == "RATE_LIMITED"
    rate_limiter.user_limit = settings.rate_limit_per_minute
    rate_limiter.tenant_limit = settings.tenant_rate_limit_per_minute
    rate_limiter.buckets.clear()


def test_attachment_policy_returns_structured_error(client):
    payload = _minimal_payload()
    payload["attachments"] = [
        {"type": "image", "url": "https://example.com/img.jpg"}
        for _ in range(settings.max_attachments + 1)
    ]
    resp = client.post("/chat/message", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["errors"][0]["code"] == "INVALID_ATTACHMENT"


def test_identity_headers_fill_missing_fields(client):
    payload = _minimal_payload()
    payload["user"].pop("tenant_id")
    payload["user"].pop("user_id")
    headers = {"X-Tenant-Id": "tenant-header", "X-User-Id": "user-header"}
    resp = client.post("/chat/message", headers=headers, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == "tenant-header"


def test_image_engine_feature_flag(client):
    settings.flag_enable_image_engine = False
    payload = _minimal_payload()
    payload["text"] = "Maize leaves have disease spots, need diagnosis."
    payload["attachments"] = [{"type": "image", "url": "https://example.com/leaf.jpg"}]
    resp = client.post("/chat/message", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert any(error["code"] == "IMAGE_ANALYSIS_UNAVAILABLE" for error in body["errors"])
    settings.flag_enable_image_engine = True
    settings.flag_enable_image_engine = True


def test_rag_citations_returned_when_enabled(client):
    orchestrator.rag.enabled = True
    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["rag_used"] is True
    assert len(body["answer"].get("citations", [])) >= 1
    orchestrator.rag.enabled = False


def test_rag_uses_index_file_when_provided(tmp_path, client):
    index_file = tmp_path / "rag.json"
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


def test_rag_disabled_adds_error_code(client):
    orchestrator.rag.enabled = False
    resp = client.post("/chat/message", json=_minimal_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert any(error["code"] == "RAG_EMPTY" for error in body["errors"])
    orchestrator.rag.enabled = True


def test_rejects_oversized_text(client):
    payload = _minimal_payload()
    payload["text"] = "a" * (settings.max_message_length + 1)
    resp = client.post("/chat/message", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["errors"][0]["code"] == "VALIDATION_ERROR"
