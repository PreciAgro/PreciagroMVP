"""Database initialization and session management for Temporal Logic Engine.

This module wraps the models module to provide the init_database, close_database,
and get_database_session interfaces expected by app.py.
"""
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import get_engine, get_session, init_tables

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database on startup."""
    try:
        await init_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped (not configured): {e}")


async def close_database():
    """Close database connections on shutdown."""
    try:
        engine = get_engine()
        if engine:
            await engine.dispose()
            logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for dependency injection."""
    Session = get_session()
    if Session is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")
    
    async with Session() as session:
        yield session
