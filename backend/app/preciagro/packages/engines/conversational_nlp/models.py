"""Pydantic models for the Conversational/NLP Engine."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


def _uuid_str() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


class Attachment(BaseModel):
    """Represents a message attachment."""

    type: str
    url: Optional[str] = None
    content_type: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None


class UserContext(BaseModel):
    """User metadata attached to a chat request."""

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    farm_id: Optional[str] = None
    farm_ids: List[str] = Field(default_factory=list)
    role: Literal["farmer", "agronomist", "admin", "internal"] = "farmer"

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "user_id" not in data and "id" in data:
                data["user_id"] = data.get("id")
            if data.get("farm_id") and data.get("farm_ids"):
                if data["farm_id"] not in data["farm_ids"]:
                    data["farm_ids"] = [data["farm_id"], *data["farm_ids"]]
        return data

    @property
    def id(self) -> str:  # Backwards compatibility
        return self.user_id or ""


class ChatMessageRequest(BaseModel):
    """Normalized chat request payload."""

    message_id: str = Field(default_factory=_uuid_str)
    session_id: str = Field(default_factory=_uuid_str)
    channel: Literal["mobile", "web", "chat_app", "internal"] = "web"
    user: UserContext
    locale: str = "en-US"
    language_preference: Optional[str] = None
    text: str
    attachments: List[Attachment] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    feedback: Optional[Literal["helpful", "not_helpful", "wrong", "harmful"]] = None

    @property
    def tenant_id(self) -> str:
        return self.user.tenant_id or ""

    @property
    def farm_id(self) -> Optional[str]:
        return self.user.farm_id or (self.user.farm_ids[0] if self.user.farm_ids else None)

    @property
    def user_id(self) -> str:
        return self.user.user_id or ""

    @property
    def user_role(self) -> str:
        return self.user.role


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


class SessionTurn(BaseModel):
    """Single conversational turn stored in session history."""

    role: Literal["user", "assistant", "system"]
    text: str
    intent: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionContext(BaseModel):
    """State persisted per session."""

    session_id: str
    user_id: str
    tenant_id: Optional[str] = None
    farm_id: Optional[str] = None
    user_role: Optional[str] = None
    channel: Optional[str] = None
    turns: List[SessionTurn] = Field(default_factory=list)
    active_task: Optional[str] = None
    last_intent: Optional[str] = None
    last_tool_outputs: Dict[str, Any] = Field(default_factory=dict)


class ToolsContext(BaseModel):
    """Typed container for tool outputs to feed into prompts."""

    geo_context: Dict[str, Any] = Field(default_factory=dict)
    temporal_logic: Dict[str, Any] = Field(default_factory=dict)
    crop_intelligence: Dict[str, Any] = Field(default_factory=dict)
    inventory: Dict[str, Any] = Field(default_factory=dict)
    image_analysis: Dict[str, Any] = Field(default_factory=dict)
    miscellaneous: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "ToolsContext":
        ctx = cls()
        for key, value in raw.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value or {})
            else:
                ctx.miscellaneous[key] = value or {}
        return ctx

    def as_dict(self) -> Dict[str, Any]:
        """Return dict representation for logging/redis."""
        return self.model_dump()


class StructuredAnswer(BaseModel):
    """Structured representation returned by AgroLLM."""

    summary: str
    steps: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    extras: Dict[str, Any] = Field(default_factory=dict)
    raw_text: Optional[str] = None


class ErrorCode(str, Enum):
    """Enumeration of supported error codes."""

    UPSTREAM_ENGINE_FAILED = "UPSTREAM_ENGINE_FAILED"
    IMAGE_ANALYSIS_UNAVAILABLE = "IMAGE_ANALYSIS_UNAVAILABLE"
    TEMPORAL_ENGINE_TIMEOUT = "TEMPORAL_ENGINE_TIMEOUT"
    NLP_FALLBACK_USED = "NLP_FALLBACK_USED"
    RAG_EMPTY = "RAG_EMPTY"
    AGROLLM_DEGRADED = "AGROLLM_DEGRADED"
    INVALID_ATTACHMENT = "INVALID_ATTACHMENT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorDetail(BaseModel):
    """Structured error contract."""

    code: ErrorCode
    message: str
    component: Optional[str] = None


class VersionManifest(BaseModel):
    """Bundle of schema/version tags included in responses."""

    intent_schema: str
    response_schema: str
    router: str
    engine_api: str


class AnswerPayload(BaseModel):
    """Rendered answer to return to the client."""

    summary: str
    steps: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    extras: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Citation] = Field(default_factory=list)
    status: Literal["ok", "degraded", "error"] = "ok"
    versions: VersionManifest
    errors: List[ErrorDetail] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    """Top-level chat response schema."""

    message_id: str
    session_id: str
    intent: str
    entities: IntentEntities
    answer: AnswerPayload
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    fallback_used: bool = False
    rag_used: bool = False
    latency_ms: Optional[int] = None
    tenant_id: Optional[str] = None
    farm_id: Optional[str] = None
    channel: Optional[str] = None
    errors: List[ErrorDetail] = Field(default_factory=list)
    versions: VersionManifest
