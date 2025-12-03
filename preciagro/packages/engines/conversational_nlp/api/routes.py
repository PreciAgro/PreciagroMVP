"""API routes for Conversational/NLP Engine."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..core.config import settings
from ..models import (
    AnswerPayload,
    ChatMessageRequest,
    ChatMessageResponse,
    ErrorCode,
    ErrorDetail,
    IntentEntities,
    VersionManifest,
)
from ..services.attachment_policy import attachment_policy
from ..services.auth import resolve_identity
from ..services.orchestrator import ConversationOrchestrator
from ..services.redaction import sanitize_payload
from ..services.security import enforce_rate_limit, require_admin_access, require_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

VERSION_MANIFEST = VersionManifest(
    intent_schema=settings.intent_schema_version,
    response_schema=settings.response_schema_version,
    router=settings.router_version,
    engine_api=settings.engine_api_version,
)


def _build_error_response(
    payload: ChatMessageRequest,
    errors: List[ErrorDetail],
    status_code: int,
) -> JSONResponse:
    """Return a ChatMessageResponse encoded as JSONResponse for error scenarios."""
    versions = VERSION_MANIFEST.model_copy()
    answer = AnswerPayload(
        summary="; ".join(error.message for error in errors),
        steps=[],
        warnings=[],
        extras={"request_id": payload.message_id, "channel": payload.channel},
        citations=[],
        status="error",
        versions=versions,
        errors=errors,
    )
    response = ChatMessageResponse(
        message_id=payload.message_id,
        session_id=payload.session_id,
        intent="validation_error",
        entities=IntentEntities(),
        answer=answer,
        tool_calls=[],
        fallback_used=False,
        rag_used=False,
        latency_ms=0,
        tenant_id=payload.tenant_id or None,
        farm_id=payload.farm_id,
        channel=payload.channel,
        errors=errors,
        versions=versions,
    )
    return JSONResponse(status_code=status_code, content=response.model_dump())


@router.post("/chat/message", response_model=ChatMessageResponse, tags=["chat"])
async def chat_message(
    payload: ChatMessageRequest,
    request: Request,
    _: None = Depends(require_api_key),
) -> ChatMessageResponse:
    orchestrator: ConversationOrchestrator = request.app.state.orchestrator
    identity = resolve_identity(request, payload)

    policy_errors = attachment_policy.validate(payload)
    if policy_errors:
        return _build_error_response(payload, policy_errors, status.HTTP_422_UNPROCESSABLE_CONTENT)

    enforce_rate_limit(identity.tenant_id, identity.user_id)

    try:
        response = await orchestrator.handle_message(payload)
        return response
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat_message failed", exc_info=exc)
        error = ErrorDetail(
            code=ErrorCode.UPSTREAM_ENGINE_FAILED,
            message="Conversation engine temporarily unavailable",
            component="orchestrator",
        )
        return _build_error_response(payload, [error], status.HTTP_503_SERVICE_UNAVAILABLE)


@router.get("/health", tags=["system"])
async def health(request: Request) -> dict[str, object]:
    orchestrator: ConversationOrchestrator = request.app.state.orchestrator
    status_str = "ok" if orchestrator.agrollm_client.has_remote_backend else "degraded"
    return {
        "status": status_str,
        "engine": "conversational-nlp",
        "versions": VERSION_MANIFEST.model_dump(),
        "features": {
            "rag": settings.rag_enabled,
            "geo": settings.flag_enable_geo_engine,
            "temporal": settings.flag_enable_temporal_engine,
            "image": settings.flag_enable_image_engine,
            "rule_based": settings.flag_force_rule_based_mode,
        },
    }


@router.get(
    "/admin/session/{session_id}",
    tags=["admin"],
    dependencies=[Depends(require_api_key), Depends(require_admin_access)],
)
async def inspect_session(session_id: str, user_id: str, request: Request) -> dict[str, object]:
    """Return sanitized session state for debugging."""
    orchestrator: ConversationOrchestrator = request.app.state.orchestrator
    session = await orchestrator.session_store.get(session_id, user_id=user_id)
    payload = session.model_dump()
    payload["turns"] = [turn.model_dump() for turn in session.turns]
    payload["sanitized"] = sanitize_payload(payload.copy())
    return {
        "session_id": session_id,
        "turn_count": len(session.turns),
        "history_enabled": settings.conversation_history_enabled,
        "session": payload,
    }
