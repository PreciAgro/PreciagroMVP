"""SQLAlchemy models for Temporal Logic Engine."""

import enum
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Enum, ForeignKey, Index, Text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class ScheduleStatus(enum.Enum):
    pending = "pending"
    scheduled = "scheduled"
    done = "done"
    skipped = "skipped"
    expired = "expired"
    cancelled = "cancelled"


class JobStatus(enum.Enum):
    queued = "queued"
    sending = "sending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class ScheduleItem(Base):
    __tablename__ = "schedule_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    farm_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    rule_id: Mapped[str] = mapped_column(Text)
    rule_hash: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(Text)
    window_start_ts: Mapped[datetime]
    window_end_ts: Mapped[datetime]
    source_event_id: Mapped[str] = mapped_column(Text)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus), default=ScheduleStatus.scheduled
    )
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Relationships
    jobs: Mapped[list["NotificationJob"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class NotificationJob(Base):
    __tablename__ = "notification_job"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedule_item.id"))
    channel: Mapped[str] = mapped_column(Text)
    send_after_ts: Mapped[datetime]
    dedupe_key: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    attempts: Mapped[int]
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Relationships
    schedule: Mapped[ScheduleItem] = relationship(back_populates="jobs")


# Indexes
Index("notification_job_dedupe_idx", NotificationJob.dedupe_key, unique=True)
Index("notification_due_idx", NotificationJob.status, NotificationJob.send_after_ts)


class TaskOutcome(Base):
    __tablename__ = "task_outcome"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedule_item.id"))
    outcome: Mapped[str] = mapped_column(Text)  # 'done' | 'skipped'
    actor: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]


class NotificationAudit(Base):
    __tablename__ = "notification_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("notification_job.id"))
    # 'enqueue'|'send_attempt'|'send_success'|'send_fail'|'receipt'
    event: Mapped[str] = mapped_column(Text)
    data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime]


# Database setup
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
