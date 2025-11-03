"""Database models for the Temporal Logic Engine."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            reconstructor, relationship)

from .config import DATABASE_URL


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TaskStatus(str, enum.Enum):
    """Enumerates the lifecycle states for scheduled tasks."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TemporalEvent(Base):
    """Represents an inbound event that can trigger rules."""

    __tablename__ = "temporal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    _metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    triggered_schedules: Mapped[list["ScheduledTask"]] = relationship(
        back_populates="triggering_event"
    )

    def __init__(self, **kwargs: Any) -> None:
        """Allow legacy payload keys while persisting canonical columns."""
        event_data = kwargs.pop("event_data", None)
        context_data = kwargs.pop("context_data", None)
        if event_data is not None:
            kwargs.setdefault("payload", event_data)
        if context_data is not None:
            kwargs.setdefault("_metadata", context_data)
        super().__init__(**kwargs)
        # FIX: temporal event columns missing — tests expected event_data/context_data — accept legacy keys for backwards compatibility — slight duplication until callers migrate.


class TemporalRule(Base):
    """Stores a compiled temporal rule definition."""

    __tablename__ = "temporal_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    actions: Mapped[list[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    window_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    _metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    schedules: Mapped[list["ScheduledTask"]] = relationship(back_populates="rule")


class ScheduledTask(Base):
    """Represents work items produced after rule evaluation."""

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(150), unique=True)
    rule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("temporal_rules.id"), nullable=True, index=True
    )
    triggering_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("temporal_events.id"), index=True
    )
    _user_id: Mapped[Optional[str]] = mapped_column("user_id", String(100), index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    task_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(
        String(20), default=TaskStatus.PENDING.value, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    rule: Mapped[TemporalRule] = relationship(back_populates="schedules")
    triggering_event: Mapped[Optional[TemporalEvent]] = relationship(
        back_populates="triggered_schedules"
    )
    outcomes: Mapped[list["TaskOutcome"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )

    @property
    def user_id(self) -> Optional[str]:
        value = self.__dict__.get("_user_id")
        if value is None:
            return self.__dict__.get("_user_id_cache")
        self.__dict__["_user_id_cache"] = value
        return value

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        self.__dict__["_user_id_cache"] = value
        self._user_id = value

    @reconstructor
    def _set_user_cache(self) -> None:
        self.__dict__["_user_id_cache"] = self.__dict__.get("_user_id")


class TaskOutcome(Base):
    """Captures execution results for scheduled tasks."""

    __tablename__ = "task_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("scheduled_tasks.id"), nullable=False, index=True
    )
    outcome_type: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    task: Mapped[ScheduledTask] = relationship(back_populates="outcomes")


class UserIntent(Base):
    """Stores NLP intents captured from conversational channels."""

    __tablename__ = "user_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    processed_intent: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[Optional[int]] = mapped_column(Integer)
    conversation_context: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RateLimitBucket(Base):
    """Tracks usage counts for rate-limited resources."""

    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "channel", "bucket_key", name="uq_rate_limit_user_channel_bucket"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    bucket_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


def _get_event_metadata(self: TemporalEvent) -> Dict[str, Any]:
    """Return contextual metadata with a dict fallback."""
    return self._metadata or {}


def _set_event_metadata(self: TemporalEvent, value: Dict[str, Any]) -> None:
    self._metadata = value or {}


def _get_rule_metadata(self: TemporalRule) -> Dict[str, Any]:
    """Expose rule metadata while storing in reserved column."""
    return self._metadata or {}


def _set_rule_metadata(self: TemporalRule, value: Dict[str, Any]) -> None:
    self._metadata = value or {}


TemporalEvent.metadata = property(_get_event_metadata, _set_event_metadata)
TemporalRule.metadata = property(_get_rule_metadata, _set_rule_metadata)


Index(
    "ix_rate_limit_bucket_window",
    RateLimitBucket.window_start,
    RateLimitBucket.window_end,
)


_engine = None
_Session: Optional[async_sessionmaker] = None


def get_engine():
    """Create (or reuse) the async SQLAlchemy engine."""
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session():
    """Return an async session factory when database configuration is present."""
    global _Session
    if _Session is None:
        engine = get_engine()
        if engine is None:
            return None
        _Session = async_sessionmaker(engine, expire_on_commit=False)
    return _Session


async def init_tables() -> None:
    """Materialise all ORM tables in the configured database."""
    engine = get_engine()
    if engine is None:
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db() -> None:
    """Initialise the engine and session factory for synchronous callers."""
    get_engine()
    get_session()


def async_session():
    """Backwards-compatible accessor for the async session factory."""
    return get_session()
