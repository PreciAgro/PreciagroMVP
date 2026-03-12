"""Conversation orchestrator that drives the full pipeline."""

from __future__ import annotations

import logging
import time
from typing import Dict, List

from ..core.config import settings
from ..models import (
    AnswerPayload,
    ChatMessageRequest,
    ChatMessageResponse,
    Citation,
    ErrorCode,
    ErrorDetail,
    IntentResult,
    SessionContext,
    ToolsContext,
    VersionManifest,
)
from .agrollm_client import AgroLLMClient, build_agrollm_client
from .logstore import ConversationLogStore
from .metrics import chat_requests_total, fallback_used_total, latency_histogram, rag_used_total
from .nlu import IntentClassifier
from .rag import RAGRetriever
from .rag_vector import VectorDBRetriever
from .response_builder import ResponseBuilder
from .router import EngineRouter
from .session import SessionStore
from .telemetry import log_turn
from .tracing import start_span

logger = logging.getLogger(__name__)

ENGINE_TO_CONTEXT_KEY: Dict[str, str] = {
    "geo-context": "geo_context",
    "temporal-logic": "temporal_logic",
    "crop-intelligence": "crop_intelligence",
    "image-analysis": "image_analysis",
    "inventory": "inventory",
}


class ConversationOrchestrator:
    """Coordinates NLU, tool routing, RAG, and response generation."""

    def __init__(self, session_store: SessionStore) -> None:
        self.session_store = session_store
        self.version_manifest = VersionManifest(
            intent_schema=settings.intent_schema_version,
            response_schema=settings.response_schema_version,
            router=settings.router_version,
            engine_api=settings.engine_api_version,
        )
        self.agrollm_client: AgroLLMClient = build_agrollm_client(settings)
        self.intent_classifier = IntentClassifier(client=self.agrollm_client)
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
        prompt_override = settings.response_system_prompt or None
        self.response_builder = ResponseBuilder(
            self.agrollm_client,
            system_prompt=prompt_override,
            force_rules_mode=settings.flag_force_rule_based_mode,
        )
        self.log_store = ConversationLogStore(
            path=settings.conversation_log_path,
            retention_days=settings.log_retention_days,
            anonymize=settings.anonymize_logs,
            history_enabled=settings.conversation_history_enabled,
        )

    async def handle_message(self, request: ChatMessageRequest) -> ChatMessageResponse:
        started = time.perf_counter()
        session_context = await self.session_store.get(request.session_id, request.user_id)
        session_context.tenant_id = request.tenant_id
        session_context.farm_id = request.farm_id
        session_context.user_role = request.user_role
        session_context.channel = request.channel
        logger.debug("Session state loaded: %s", session_context)
        cached_tools = session_context.last_tool_outputs or {}

        stage_latencies: Dict[str, int] = {}
        errors: List[ErrorDetail] = []

        with start_span("intent_classify"):
            intent_result = await self.intent_classifier.classify(request, session_context)
        stage_latencies["intent_ms"] = int((time.perf_counter() - started) * 1000)

        with start_span("router_call"):
            tools_context, tool_calls, router_errors = await self.router.route(
                intent_result, request
            )
        errors.extend(router_errors)
        stage_latencies["tools_ms"] = (
            int((time.perf_counter() - started) * 1000) - stage_latencies["intent_ms"]
        )

        with start_span("rag_retrieve"):
            citations = await self._retrieve_citations(
                intent_result, tools_context, request.text, errors
            )
        stage_latencies["rag_ms"] = (
            int((time.perf_counter() - started) * 1000)
            - stage_latencies["intent_ms"]
            - stage_latencies["tools_ms"]
        )

        degraded_calls = [c for c in tool_calls if c.status in {"degraded", "disabled"}]
        router_warning = False
        if degraded_calls and cached_tools:
            for call in degraded_calls:
                ctx_key = ENGINE_TO_CONTEXT_KEY.get(call.engine)
                if ctx_key and ctx_key in cached_tools:
                    setattr(tools_context, ctx_key, cached_tools.get(ctx_key))
                    call.status = "cached"
        elif degraded_calls and not cached_tools:
            router_warning = True

        with start_span("response_build"):
            answer, fallback_used = await self.response_builder.build_answer(
                request=request,
                intent=intent_result,
                session_context=session_context,
                tools_context=tools_context,
                citations=citations,
                base_errors=errors,
                versions=self.version_manifest.model_copy(),
            )
        stage_latencies["llm_ms"] = (
            int((time.perf_counter() - started) * 1000)
            - stage_latencies["intent_ms"]
            - stage_latencies["tools_ms"]
            - stage_latencies["rag_ms"]
        )

        if router_warning:
            answer.warnings.append("Some connectors were unavailable; partial guidance shown.")
            answer.status = "degraded"

        session_context.last_intent = intent_result.intent
        session_context.last_tool_outputs = tools_context.as_dict()
        self._append_turns(session_context, request, intent_result.intent, answer, fallback_used)
        await self.session_store.save(session_context)
        if not settings.conversation_history_enabled:
            await self.session_store.delete(session_context.session_id)

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
            tenant_id=request.tenant_id or None,
            farm_id=request.farm_id,
            channel=request.channel,
            errors=answer.errors,
            versions=answer.versions,
        )

        chat_requests_total.labels(status=answer.status).inc()
        if fallback_used:
            fallback_used_total.inc()
        if citations:
            rag_used_total.inc()
        latency_histogram.observe(latency_ms)

        log_turn(
            request=request,
            response=response,
            stage_latencies_ms=stage_latencies,
            session_context=session_context,
        )
        await self.log_store.persist_turn(
            request=request,
            response=response,
            session_context=session_context,
            tools_context=tools_context,
            stage_latencies=stage_latencies,
        )

        return response

    async def _retrieve_citations(
        self,
        intent: IntentResult,
        tools_context: ToolsContext,
        user_message: str,
        errors: List[ErrorDetail],
    ) -> List[Citation]:
        """Wrapper to fetch RAG snippets and capture degrade codes."""
        if not getattr(self.rag, "enabled", False):
            errors.append(
                ErrorDetail(
                    code=ErrorCode.RAG_EMPTY,
                    message="RAG disabled via FLAG_ENABLE_RAG.",
                    component="rag",
                )
            )
            return []
        try:
            citations = await self.rag.retrieve(
                intent=intent,
                tools_context=tools_context,
                user_message=user_message,
            )
            if not citations:
                errors.append(
                    ErrorDetail(
                        code=ErrorCode.RAG_EMPTY,
                        message="RAG returned no supporting documents.",
                        component="rag",
                    )
                )
            return citations
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG retrieval failed: %s", exc)
            errors.append(
                ErrorDetail(
                    code=ErrorCode.RAG_EMPTY,
                    message=f"RAG failure: {exc}",
                    component="rag",
                )
            )
            return []

    def _append_turns(
        self,
        session_context: SessionContext,
        request: ChatMessageRequest,
        intent_name: str,
        answer: AnswerPayload,
        fallback_used: bool,
    ) -> None:
        """Persist user + assistant turns with metadata."""
        self.session_store.append_turn(
            session_context,
            role="user",
            text=request.text,
            intent=intent_name,
            metadata={
                "channel": request.channel,
                "tenant_id": request.tenant_id,
                "feedback": request.feedback,
            },
        )
        assistant_text = answer.summary
        if answer.steps:
            assistant_text = f"{assistant_text}\nSteps: {' | '.join(answer.steps[:3])}"
        self.session_store.append_turn(
            session_context,
            role="assistant",
            text=assistant_text,
            intent=intent_name,
            metadata={
                "fallback_used": fallback_used,
                "status": answer.status,
            },
        )
