"""Base database models for Farm Inventory Engine."""

from __future__ import annotations

import logging
from sqlalchemy.orm import DeclarativeBase


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


def register_models() -> None:
    """Import modules that register SQLAlchemy models.

    Alembic and SQLAlchemy need the model classes imported so they are attached
    to the Base metadata. We keep the imports local to avoid circular imports.
    """
    # pylint: disable=import-outside-toplevel
    from . import models  # noqa: F401


# Ensure model modules are imported when this module loads.
try:
    register_models()
except Exception:  # pragma: no cover - defensive logging
    logger.exception("Failed to register Farm Inventory models")

