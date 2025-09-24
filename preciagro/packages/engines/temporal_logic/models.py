"""SQLAlchemy models for Temporal Logic Engine."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Text, Enum, JSON, ForeignKey, Index
from datetime import datetime
import enum
import os
from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class ScheduleItem(Base):
    __tablename__ = "schedule_item"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    rule_id: Mapped[str] = mapped_column(Text)
    schedule_time: Mapped[datetime]
    payload: Mapped[dict] = mapped_column(JSON)
    target: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="pending")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class TaskOutcome(Base):
    __tablename__ = "task_outcome"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime]
    task_metadata: Mapped[dict] = mapped_column(JSON)


# Database setup - lazy initialization
_engine = None
_Session = None


def get_engine():
    """Get database engine, creating it if necessary."""
    global _engine
    if _engine is None:
        if DATABASE_URL is None:
            raise ValueError("DATABASE_URL environment variable is required")
        _engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session():
    """Get session factory, creating it if necessary."""
    global _Session
    if _Session is None:
        _Session = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _Session


def async_session():
    """Get async database session context manager."""
    Session = get_session()
    return Session()


async def init_tables():
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db():
    """Initialize database engine."""
    get_engine()
    get_session()
