"""Telemetry helpers for conversational engine."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..models import ChatMessageRequest, ChatMessageResponse
from .redaction import sanitize_payload


logger = logging.getLogger(__name__)


def log_turn(
    request: ChatMessageRequest,
    response: ChatMessageResponse,
    stage_latencies_ms: Dict[str, int],
    ) -> None:
        """Emit a structured log for a completed turn."""
        try:
            payload: Dict[str, Any] = {
                "event": "conversation_turn",
                "message_id": request.message_id,
                "session_id": request.session_id,
                "user_id": "<redacted>",
                "intent": response.intent,
                "entities": response.entities.model_dump(),
                "tool_calls": [call.model_dump() for call in response.tool_calls],
                "fallback_used": response.fallback_used,
                "rag_used": response.rag_used,
                "latency_ms": response.latency_ms,
                "stage_latencies_ms": stage_latencies_ms,
            }
            payload["request_sanitized"] = sanitize_payload(request.model_dump())
            logger.info(payload)
        except Exception:  # noqa: BLE001
            logger.debug("Telemetry logging failed", exc_info=True)
