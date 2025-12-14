"""API package - FastAPI routes for FLE."""

from .feedback_routes import router as feedback_router
from .learning_routes import router as learning_router
from .admin_routes import router as admin_router

__all__ = [
    "feedback_router",
    "learning_router",
    "admin_router",
]
