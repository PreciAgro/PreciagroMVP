"""Unit tests for key conversational components."""

from __future__ import annotations

from pathlib import Path

import pytest

from preciagro.packages.engines.conversational_nlp.models import (
    ChatMessageRequest,
    Citation,
    IntentEntities,
    IntentResult,
    SessionContext,
    ToolsContext,
    UserContext,
    VersionManifest,
)
from preciagro.packages.engines.conversational_nlp.services.agrollm_client import (
    AgroLLMClient,
    StubAgroLLMBackend,
)
from preciagro.packages.engines.conversational_nlp.services.nlu import IntentClassifier
from preciagro.packages.engines.conversational_nlp.services.rag import RAGRetriever
from preciagro.packages.engines.conversational_nlp.services.response_builder import ResponseBuilder
from preciagro.packages.engines.conversational_nlp.services.router import EngineRouter


def _chat_request(text: str = "When should I plant maize?") -> ChatMessageRequest:
    return ChatMessageRequest(
        message_id="msg-test",
        session_id="sess-test",
        channel="web",
        user=UserContext(
            user_id="user-1",
            tenant_id="tenant-1",
            farm_id="farm-1",
            farm_ids=["farm-1"],
            role="farmer",
        ),
        locale="en-US",
        text=text,
        metadata={"location": "Murewa"},
    )


@pytest.mark.asyncio
async def test_intent_classifier_stub_backend():
    classifier = IntentClassifier(client=AgroLLMClient(StubAgroLLMBackend()))
    session = SessionContext(session_id="sess-test", user_id="user-1")
    result = await classifier.classify(_chat_request(), session)
    assert result.intent == "plan_planting"
    assert result.entities.crop == "maize"


@pytest.mark.asyncio
async def test_router_returns_structured_tools_context():
    router = EngineRouter()
    intent = IntentResult(intent="plan_planting", entities=IntentEntities(crop="maize"))
    tools_context, calls, errors = await router.route(intent, _chat_request())
    assert tools_context.geo_context
    assert tools_context.temporal_logic
    assert any(call.engine == "geo-context" for call in calls)
    assert isinstance(errors, list)


@pytest.mark.asyncio
async def test_response_builder_uses_stub_agrollm():
    agrollm = AgroLLMClient(StubAgroLLMBackend())
    builder = ResponseBuilder(agrollm)
    request = _chat_request()
    session = SessionContext(session_id="sess", user_id="user", tenant_id="tenant-1")
    intent = IntentResult(intent="plan_planting", entities=IntentEntities(crop="maize"))
    tools_context = ToolsContext.from_raw(
        {"temporal_logic": {"recommended_window": "mid-November"}}
    )
    citations = [Citation(source="rag", id="zim_maize_window", snippet="Plant mid-November.")]
    versions = VersionManifest(
        intent_schema="intent-test",
        response_schema="response-test",
        router="router-test",
        engine_api="engine-test",
    )
    answer, fallback = await builder.build_answer(
        request=request,
        intent=intent,
        session_context=session,
        tools_context=tools_context,
        citations=citations,
        base_errors=[],
        versions=versions,
    )
    assert fallback is False
    assert "mid-November" in answer.summary
    assert answer.citations


@pytest.mark.asyncio
async def test_rag_retriever_returns_seed_docs(tmp_path):
    data_path = Path("preciagro/packages/engines/conversational_nlp/data/rag_seed.json")
    retriever = RAGRetriever(enabled=True, top_k=2, index_path=str(data_path))
    intent = IntentResult(intent="plan_planting", entities=IntentEntities(crop="maize"))
    tools_context = ToolsContext()
    citations = await retriever.retrieve(
        intent=intent, tools_context=tools_context, user_message="plant maize window"
    )
    assert citations
    assert citations[0].id in {"zim_maize_window", "pesticide_label_safety"}
