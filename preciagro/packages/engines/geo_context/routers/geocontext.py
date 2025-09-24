"""Router shim for geo_context engine."""
from fastapi import APIRouter
from ..api.routes.api import router as api_router

# Create main router for geo_context engine
router = APIRouter()

# Include API routes
router.include_router(api_router)
