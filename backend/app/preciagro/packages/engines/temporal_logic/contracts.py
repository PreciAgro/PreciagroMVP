"""Core contracts and Pydantic models for Temporal Logic Engine."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator
from pydantic.config import ConfigDict

from .contracts_old import (
    Action,
    BulkOperationResponse,  # noqa: F401
    ChannelType,
    Condition,
    EventBase,
    EventCreate,
    EventResponse,
    EventType,
    HealthCheck,
    IntentBase,
    IntentCreate,
    IntentResponse,
    MessageRequest,
    MessageTemplate,
    OutcomeBase,
    OutcomeCreate,
    OutcomeResponse,
    PaginatedResponse,
    ProcessedIntent,
    RuleBase,
    RuleCreate,
    RuleResponse,
    RuleUpdate,
    ScheduledTaskBase,
    ScheduledTaskCreate,
    ScheduledTaskResponse,
    ScheduledTaskUpdate,
    TaskConfig,
    TaskStatus,
    WindowConfig,
)

# Event coming from other engines (e.g., diagnosis)


class EngineEvent(BaseModel):
    """Inbound event from another engine."""

    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(
        ...,
        validation_alias=AliasChoices("event_id", "id"),
    )
    event_type: str = Field(
        ...,
        validation_alias=AliasChoices("event_type", "topic"),
    )
    user_id: Optional[str] = None
    farm_id: str
    timestamp: datetime = Field(
        ...,
        validation_alias=AliasChoices("timestamp", "ts_utc"),
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    farmer_tz: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("farmer_tz", "timezone"),
    )
    source: Optional[str] = None

    @property
    def id(self) -> str:
        """Legacy accessor for event identifier."""
        return self.event_id

    @property
    def topic(self) -> str:
        """Legacy accessor for event topic."""
        return self.event_type

    @property
    def ts_utc(self) -> datetime:
        """Legacy accessor for timestamp."""
        return self.timestamp


# === DSL types ===
Op = Literal["<", "<=", " >", ">=", "equals", "in", "not_in"]


class Clause(BaseModel):
    """Single predicate clause used in triggers."""

    key: str
    op: Op
    value: Any
    weight: float = 1.0


class Trigger(BaseModel):
    """Trigger definition for a rule."""

    model_config = ConfigDict(populate_by_name=True)

    event_type: str = Field(
        ...,
        validation_alias=AliasChoices("event_type", "topic"),
    )
    filters: List[Any] = Field(default_factory=list)
    when: List[Clause] = Field(default_factory=list)

    @property
    def topic(self) -> str:
        """Expose topic-style accessor for backwards compatibility."""
        return self.event_type


class Preconditions(BaseModel):
    """Optional preconditions grouping."""

    all: List[Clause] = []
    any: List[Clause] = []


class PreferredSubwindow(BaseModel):
    """Preferred delivery window expressed in local time."""

    start_local: Optional[str] = None
    end_local: Optional[str] = None


class Window(BaseModel):
    """Delivery window offsets."""

    id: str = "window"
    channel: str = "sms"
    message: str = ""
    delay: Optional[str] = None
    time: Optional[str] = None
    start_offset_hours: Optional[int] = None
    end_offset_hours: Optional[int] = None
    start_at_local: Optional[str] = None
    end_at_local: Optional[str] = None
    day_offset: int = 0
    preferred_subwindow: Optional[PreferredSubwindow] = None


class ScheduleWindow(Window):
    """Alias class retaining legacy name."""

    pass


class Dedupe(BaseModel):
    """Deduplication scope for compiled tasks."""

    scope: str = "global"
    window: str = "24h"
    fields: List[str] = Field(default_factory=list)
    ttl_hours: int = 24


class Deduplication(Dedupe):
    """Legacy alias for deduplication configuration."""

    pass


class Message(BaseModel):
    """Structured message payload."""

    short: str
    long: Optional[str] = None
    buttons: List[str] = []


class Rule(BaseModel):
    """High level DSL rule representation."""

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy(cls, data: Any):
        """Normalize legacy payloads before validation."""
        if not isinstance(data, dict):
            return data

        result = dict(data)

        if "window" in result and "windows" not in result:
            window_value = result.pop("window")
            result["windows"] = [window_value] if window_value else []

        if "dedupe" in result and "deduplication" not in result:
            result["deduplication"] = result.pop("dedupe")

        if "windows" in result:
            normalized_windows = []
            for window in result.get("windows", []):
                if isinstance(window, ScheduleWindow):
                    normalized_windows.append(window)
                elif isinstance(window, Window):
                    normalized_windows.append(ScheduleWindow.model_validate(window.model_dump()))
                else:
                    normalized_windows.append(ScheduleWindow.model_validate(window))
            result["windows"] = normalized_windows

        if "deduplication" in result and result["deduplication"] is not None:
            dedupe_value = result["deduplication"]
            if isinstance(dedupe_value, Dedupe):
                dedupe_value = dedupe_value.model_dump()
            result["deduplication"] = Deduplication.model_validate(dedupe_value)

        return result

    id: str
    version: int = 1
    trigger: Trigger
    windows: List[ScheduleWindow] = Field(default_factory=list)
    deduplication: Optional[Deduplication] = Field(
        default=None,
        validation_alias=AliasChoices("deduplication", "dedupe"),
    )
    priority: Literal["low", "medium", "high"] = "medium"
    channels: List[Literal["whatsapp", "sms", "email", "push"]] = ["whatsapp"]
    message: Optional[Message] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def window(self) -> Optional[ScheduleWindow]:
        """Return the first window for legacy access patterns."""
        return self.windows[0] if self.windows else None

    @property
    def dedupe(self) -> Optional[Deduplication]:
        """Alias for deduplication configuration."""
        return self.deduplication


class TaskOutcomePost(BaseModel):
    """Public outcome payload accepted by API routes."""

    task_id: str
    user_id: str
    outcome: Literal["done", "skipped"]
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskCreate(ScheduledTaskCreate):
    """Backwards compatible alias for scheduled task creation payloads."""


class TaskResponse(ScheduledTaskResponse):
    """Backwards compatible alias for scheduled task responses."""
