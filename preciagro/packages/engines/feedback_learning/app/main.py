"""Main FastAPI application for Feedback & Learning Engine.

FLE is a learning observer engine that:
- Captures feedback from upstream engines (UX, Diagnosis, Trust, etc.)
- Validates, weights, and translates feedback into learning signals
- Routes signals to downstream engines (Evaluation, Model Orchestration, PIE)

FLE never influences real-time decisions or calls models directly.
All data is append-only and auditable.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from typing import Dict, Any

from .api.feedback_routes import router as feedback_router
from .api.learning_routes import router as learning_router
from .api.admin_routes import router as admin_router
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting Feedback & Learning Engine v{settings.VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Feedback & Learning Engine")


# Create FastAPI app
app = FastAPI(
    title="PreciAgro Feedback & Learning Engine (FLE)",
    description=(
        "Learning observer engine that captures feedback, validates, weights, "
        "and routes learning signals to downstream engines. Acts as a learning "
        "backbone for continuous improvement without influencing real-time decisions."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

# Include routers
app.include_router(feedback_router)
app.include_router(learning_router)
app.include_router(admin_router)

# Prometheus metrics
if settings.ENABLE_PROMETHEUS:
    app.mount("/metrics", make_asgi_app())


@app.get("/")
def root() -> Dict[str, Any]:
    """Root info endpoint."""
    return {
        "service": "Feedback & Learning Engine",
        "status": "operational",
        "version": settings.VERSION,
        "description": (
            "Learning observer that captures feedback, validates, weights, "
            "and routes learning signals. Never influences real-time decisions."
        ),
        "engine_type": "learning_observer",
        "boundaries": {
            "does": [
                "Observe feedback",
                "Validate feedback quality",
                "Weight feedback by farmer experience",
                "Translate to learning signals",
                "Route to downstream engines",
            ],
            "does_not": [
                "Generate recommendations",
                "Call CV/NLP/LLM models",
                "Retrain or fine-tune models",
                "Override decisions",
                "Delete historical data",
            ],
        },
    }


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> Dict[str, Any]:
    """Readiness check endpoint.
    
    Returns information about service dependencies.
    """
    # In production, check Redis, PostgreSQL, etc.
    return {
        "ready": True,
        "dependencies": {
            "redis": "mock",  # Would check actual connection
            "postgres": "mock",  # Would check actual connection
            "celery": "configured",
        },
    }


@app.get("/config")
def get_config() -> Dict[str, Any]:
    """Get non-sensitive configuration info."""
    return {
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "supported_regions": settings.SUPPORTED_REGIONS,
        "max_feedback_per_recommendation": settings.MAX_FEEDBACK_PER_RECOMMENDATION,
        "cross_region_propagation": settings.CROSS_REGION_PROPAGATION,
        "weighting_formula": (
            "Weight = base_confidence × farmer_experience_factor × "
            "historical_accuracy_factor × model_confidence_factor × "
            "environmental_stability_factor"
        ),
        "streams": {
            "evaluation": settings.STREAM_EVALUATION,
            "model_orchestration": settings.STREAM_MODEL_ORCHESTRATION,
            "pie": settings.STREAM_PIE,
            "hitl": settings.STREAM_HITL,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "preciagro.packages.engines.feedback_learning.app.main:app",
        host="0.0.0.0",
        port=8107,
        reload=settings.DEBUG,
    )
