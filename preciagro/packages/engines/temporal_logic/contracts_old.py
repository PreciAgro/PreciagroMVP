"""Pydantic schemas for temporal logic engine."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, validator


class EventType(str, Enum):
    """Available event types."""

    WEATHER_UPDATE = "weather_update"
    CROP_STAGE_CHANGE = "crop_stage_change"
    IRRIGATION_COMPLETE = "irrigation_complete"
    PEST_DETECTION = "pest_detection"
    DISEASE_DETECTION = "disease_detection"
    SENSOR_READING = "sensor_reading"
    USER_ACTION = "user_action"
    SCHEDULE_REMINDER = "schedule_reminder"


class TaskStatus(str, Enum):
    """Task execution statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChannelType(str, Enum):
    """Available communication channels."""

    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


# Event Schemas
class EventBase(BaseModel):
    """Base event schema."""

    event_type: EventType
    source: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = {}


class EventCreate(EventBase):
    """Schema for creating events."""
    @validator("payload")
    def ensure_payload(cls, value):
        # FIX: Ruff F811 lint — fold validation into primary EventCreate to avoid duplicate class while preserving behaviour.
        if not value:
            raise ValueError("Payload cannot be empty")
        return value

    pass


class EventResponse(EventBase):
    """Schema for event responses."""

    id: int
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Rule Schemas
class WindowConfig(BaseModel):
    """Time window configuration for rules."""

    type: Literal["sliding", "tumbling", "session"]
    size: int  # in seconds
    advance: Optional[int] = None  # for sliding windows
    session_timeout: Optional[int] = None  # for session windows


class Condition(BaseModel):
    """Individual condition in a rule."""

    field: str
    operator: Literal[
        "eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "exists"
    ]
    value: Any
    weight: float = 1.0


class Action(BaseModel):
    """Action to take when rule is triggered."""

    type: Literal["message", "webhook", "schedule", "alert"]
    config: Dict[str, Any]
    delay: int = 0  # delay in seconds before executing
    channel: Optional[ChannelType] = None


class RuleBase(BaseModel):
    """Base rule schema."""

    name: str
    description: Optional[str] = None
    conditions: List[Condition]
    actions: List[Action]
    window_config: WindowConfig
    enabled: bool = True


class RuleCreate(RuleBase):
    """Schema for creating rules."""
    @validator("conditions")
    def ensure_conditions(cls, value):
        # FIX: Ruff F811 lint — consolidate validation on canonical RuleCreate to eliminate duplicate subclass.
        if not value:
            raise ValueError("At least one condition is required")
        return value

    @validator("actions")
    def ensure_actions(cls, value):
        if not value:
            raise ValueError("At least one action is required")
        return value

    pass


class RuleUpdate(BaseModel):
    """Schema for updating rules."""

    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[Condition]] = None
    actions: Optional[List[Action]] = None
    window_config: Optional[WindowConfig] = None
    enabled: Optional[bool] = None


class RuleResponse(RuleBase):
    """Schema for rule responses."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Task Schemas
class TaskConfig(BaseModel):
    """Task configuration."""

    message: Optional[str] = None
    recipient: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_payload: Optional[Dict[str, Any]] = None
    template_id: Optional[str] = None
    template_params: Optional[Dict[str, Any]] = None


class ScheduledTaskBase(BaseModel):
    """Base scheduled task schema."""

    task_type: str
    task_config: TaskConfig
    scheduled_for: datetime
    max_attempts: int = 3


class ScheduledTaskCreate(ScheduledTaskBase):
    """Schema for creating scheduled tasks."""

    rule_id: int
    triggering_event_id: Optional[int] = None


class ScheduledTaskUpdate(BaseModel):
    """Schema for updating scheduled tasks."""

    scheduled_for: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    max_attempts: Optional[int] = None


class ScheduledTaskResponse(ScheduledTaskBase):
    """Schema for scheduled task responses."""

    id: int
    rule_id: int
    triggering_event_id: Optional[int] = None
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus
    attempts: int
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Outcome Schemas
class OutcomeBase(BaseModel):
    """Base outcome schema."""

    outcome_type: str
    outcome_data: Dict[str, Any]
    source: Optional[str] = None


class OutcomeCreate(OutcomeBase):
    """Schema for creating outcomes."""

    task_id: int


class OutcomeResponse(OutcomeBase):
    """Schema for outcome responses."""

    id: int
    task_id: int
    recorded_at: datetime

    class Config:
        from_attributes = True


# Intent Schemas
class IntentBase(BaseModel):
    """Base intent schema."""

    user_id: str
    channel: ChannelType
    raw_input: str
    conversation_context: Dict[str, Any] = {}


class IntentCreate(IntentBase):
    """Schema for creating intents."""

    pass


class ProcessedIntent(BaseModel):
    """Processed intent data."""

    intent_type: str
    entities: Dict[str, Any] = {}
    confidence_score: Optional[int] = None
    suggested_actions: List[str] = []


class IntentResponse(IntentBase):
    """Schema for intent responses."""

    id: int
    processed_intent: ProcessedIntent
    confidence_score: Optional[int] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Message Schemas
class MessageTemplate(BaseModel):
    """Message template schema."""

    id: str
    content: str
    parameters: List[str] = []
    channel_specific: Dict[ChannelType, Dict[str, Any]] = {}


class MessageRequest(BaseModel):
    """Message sending request."""

    recipient: str
    channel: ChannelType
    template_id: Optional[str] = None
    content: Optional[str] = None
    template_params: Dict[str, Any] = {}
    priority: int = 5  # 1-10, higher is more urgent


# API Response Schemas
class HealthCheck(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime
    version: str
    checks: Dict[str, Dict[str, Any]]


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""

    processed: int
    succeeded: int
    failed: int
    errors: List[Dict[str, Any]] = []


class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


