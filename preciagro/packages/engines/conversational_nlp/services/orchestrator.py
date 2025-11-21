"""Conversation orchestrator that drives the full pipeline."""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..clients.agro_llm import AgroLLMClient
from ..core.config import settings
from ..models import ChatMessageRequest, ChatMessageResponse
from .llm import ResponseGenerator
from .nlu import IntentClassifier
from .rag import RAGRetriever
from .rag_vector import VectorDBRetriever
from .metrics import chat_requests_total, fallback_used_total, latency_histogram, rag_used_total
from .router import EngineRouter
from .session import SessionStore
from .telemetry import log_turn
from .tracing import start_span


logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """Coordinates NLU, tool routing, RAG, and response generation."""

    def __init__(self, session_store: SessionStore) -> None:
        self.session_store = session_store
        self.intent_classifier = IntentClassifier(
            client=AgroLLMClient(
                url=settings.agrollm_classify_url,
                api_key=settings.agrollm_api_key,
                timeout_seconds=settings.agrollm_timeout_seconds,
            )
        )
        self.router = EngineRouter()
        if settings.rag_backend.lower() == "qdrant":
            self.rag = VectorDBRetriever(
                enabled=settings.rag_enabled,
                top_k=settings.rag_top_k,
                index_path=settings.rag_index_path or None,
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                collection=settings.qdrant_collection,
                embedder_model=(
                    None if settings.qdrant_host == ":memory:" else settings.rag_embedder_model
                ),
            )
        else:
            self.rag = RAGRetriever(
                enabled=settings.rag_enabled,
                top_k=settings.rag_top_k,
                index_path=settings.rag_index_path or None,
            )
        self.response_generator = ResponseGenerator(
            AgroLLMClient(
                url=settings.agrollm_generate_url,
                api_key=settings.agrollm_api_key,
                timeout_seconds=settings.agrollm_timeout_seconds,
            )
        )

    async def handle_message(self, request: ChatMessageRequest) -> ChatMessageResponse:
        started = time.perf_counter()
        session_state = await self.session_store.get(request.session_id)
        logger.debug("Session state loaded: %s", session_state)
        cached_tools = session_state.get("last_tool_outputs", {}) if session_state else {}

        stage_latencies = {}

        with start_span("intent_classify"):
            intent_result = await self.intent_classifier.classify(request)
        stage_latencies["intent_ms"] = int((time.perf_counter() - started) * 1000)

        with start_span("router_call"):
            tool_outputs, tool_calls = await self.router.route(intent_result, request)
        stage_latencies["tools_ms"] = int((time.perf_counter() - started) * 1000) - stage_latencies["intent_ms"]

        with start_span("rag_retrieve"):
            citations = await self.rag.retrieve(intent_result)
        stage_latencies["rag_ms"] = (
            int((time.perf_counter() - started) * 1000)
            - stage_latencies["intent_ms"]
            - stage_latencies["tools_ms"]
        )
        degraded_calls = [c for c in tool_calls if c.status == "degraded"]
        # If degraded, try to reuse cached tool outputs
        if degraded_calls and cached_tools:
            for call in degraded_calls:
                if call.engine in cached_tools:
                    tool_outputs[call.engine] = cached_tools[call.engine]
                    call.status = "cached"
        with start_span("llm_generate"):
            answer, fallback_used = await self.response_generator.generate(
                request=request,
                intent=intent_result,
                tool_outputs=tool_outputs,
                citations=citations,
            )
        stage_latencies["llm_ms"] = (
            int((time.perf_counter() - started) * 1000)
            - stage_latencies["intent_ms"]
            - stage_latencies["tools_ms"]
            - stage_latencies["rag_ms"]
        )
        partial_note = ""
        if degraded_calls and not cached_tools:
            partial_note = "Some tools were unavailable; returning partial guidance."
        if partial_note:
            answer.text = f"{answer.text}\nNote: {partial_note}"

        await self.session_store.set(
            request.session_id,
            {
                "last_intent": intent_result.intent,
                "last_updated": time.time(),
                "last_tool_outputs": tool_outputs,
            },
        )

        latency_ms = int((time.perf_counter() - started) * 1000)

        response = ChatMessageResponse(
            message_id=request.message_id,
            session_id=request.session_id,
            intent=intent_result.intent,
            entities=intent_result.entities,
            answer=answer,
            tool_calls=tool_calls,
            fallback_used=fallback_used,
            rag_used=bool(citations),
            latency_ms=latency_ms,
        )

        chat_requests_total.labels(status="ok").inc()
        if fallback_used:
            fallback_used_total.inc()
        if citations:
            rag_used_total.inc()
        latency_histogram.observe(latency_ms)

        log_turn(request=request, response=response, stage_latencies_ms=stage_latencies)

        return response
