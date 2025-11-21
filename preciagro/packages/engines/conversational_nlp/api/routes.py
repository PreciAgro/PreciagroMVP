"""API routes for Conversational/NLP Engine."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..models import ChatMessageRequest, ChatMessageResponse
from ..services.orchestrator import ConversationOrchestrator
from ..services.security import enforce_rate_limit, require_api_key
from ..services.redaction import sanitize_payload


router = APIRouter()
logger = logging.getLogger(__name__)


MAX_ATTACHMENTS = 5
ALLOWED_ATTACHMENT_TYPES = {"image", "document"}


def _validate_payload(payload: ChatMessageRequest) -> None:
    if len(payload.text or "") > 12000:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Message too long")
    if len(payload.attachments) > MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Too many attachments (max {MAX_ATTACHMENTS})",
        )
    for att in payload.attachments:
        if att.type not in ALLOWED_ATTACHMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported attachment type: {att.type}",
            )
        if not att.url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Attachment url is required",
            )


@router.post("/chat/message", response_model=ChatMessageResponse, tags=["chat"])
async def chat_message(
    payload: ChatMessageRequest,
    request: Request,
    _: None = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
) -> ChatMessageResponse:
    _validate_payload(payload)
    orchestrator: ConversationOrchestrator = request.app.state.orchestrator
    try:
        return await orchestrator.handle_message(payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat_message failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation engine temporarily unavailable",
        ) from exc


@router.get("/health", tags=["system"])
async def health(request: Request) -> dict[str, str]:
    orchestrator: ConversationOrchestrator = request.app.state.orchestrator
    status_str = "degraded" if orchestrator.response_generator.client.enabled is False else "ok"
    return {"status": status_str, "engine": "conversational-nlp"}
