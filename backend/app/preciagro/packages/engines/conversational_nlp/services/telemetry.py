"""Telemetry helpers for conversational engine."""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..models import ChatMessageRequest, ChatMessageResponse, SessionContext
from .redaction import sanitize_payload

logger = logging.getLogger(__name__)


def log_turn(
    request: ChatMessageRequest,
    response: ChatMessageResponse,
    stage_latencies_ms: Dict[str, int],
    session_context: SessionContext,
) -> None:
    """Emit a structured log for a completed turn."""
    try:
        payload: Dict[str, Any] = {
            "event": "conversation_turn",
            "message_id": request.message_id,
            "session_id": request.session_id,
            "tenant_id": request.tenant_id,
            "farm_id": request.farm_id,
            "user_id": request.user_id,
            "channel": request.channel,
            "intent": response.intent,
            "entities": response.entities.model_dump(),
            "tool_calls": [call.model_dump() for call in response.tool_calls],
            "fallback_used": response.fallback_used,
            "rag_used": response.rag_used,
            "latency_ms": response.latency_ms,
            "stage_latencies_ms": stage_latencies_ms,
            "turn_count": len(session_context.turns),
            "active_task": session_context.active_task,
            "status": response.answer.status,
            "errors": [error.model_dump() for error in response.errors],
            "versions": response.versions.model_dump(),
            "feedback": request.feedback,
        }
        payload["request_sanitized"] = sanitize_payload(request.model_dump())
        logger.info(payload)
    except Exception:  # noqa: BLE001
        logger.debug("Telemetry logging failed", exc_info=True)
