"""Pydantic models for the Conversational/NLP Engine."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _uuid_str() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


class Attachment(BaseModel):
    """Represents a message attachment."""

    type: str
    url: Optional[str] = None
    content_type: Optional[str] = None


class UserContext(BaseModel):
    """User metadata attached to a chat request."""

    id: str
    farm_ids: List[str] = Field(default_factory=list)
    role: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """Normalized chat request payload."""

    message_id: str = Field(default_factory=_uuid_str)
    session_id: str = Field(default_factory=_uuid_str)
    channel: str = "web"
    user: UserContext
    locale: str = "en-US"
    text: str
    attachments: List[Attachment] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentEntities(BaseModel):
    """Extracted entities from NLU."""

    crop: Optional[str] = None
    location: Optional[str] = None
    field_name: Optional[str] = None
    season_or_date: Optional[str] = None
    problem_type: Optional[str] = None
    urgency: Optional[str] = None
    language: Optional[str] = None


class IntentResult(BaseModel):
    """Intent classification output."""

    intent: str = "general_question"
    entities: IntentEntities = Field(default_factory=IntentEntities)
    confidence: float = 0.5
    schema_version: str = "v0"


class ToolCallRecord(BaseModel):
    """Metadata about connector calls."""

    engine: str
    status: str
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class Citation(BaseModel):
    """Represents a RAG citation."""

    source: str
    id: str
    snippet: Optional[str] = None


class AnswerBlock(BaseModel):
    """Rendered answer to return to the client."""

    text: str
    bullets: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    """Top-level chat response schema."""

    message_id: str
    session_id: str
    intent: str
    entities: IntentEntities
    answer: AnswerBlock
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    fallback_used: bool = False
    rag_used: bool = False
    latency_ms: Optional[int] = None
