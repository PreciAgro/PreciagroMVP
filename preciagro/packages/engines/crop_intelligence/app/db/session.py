from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from ..core.config import settings
from .base import Base


engine = create_engine(
    settings.DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_session() -> Session:
    """FastAPI dependency that yields a scoped session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - ensures rollback on failure
        session.rollback()
        raise
    finally:
        session.close()


# Helpful for local development when migrations have not yet been executed.
if settings.AUTO_CREATE_SCHEMA:
    Base.metadata.create_all(bind=engine, checkfirst=True)
