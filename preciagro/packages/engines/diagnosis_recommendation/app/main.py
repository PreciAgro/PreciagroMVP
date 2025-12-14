"""Main FastAPI application for Diagnosis & Recommendation Engine."""

from fastapi import FastAPI
from prometheus_client import make_asgi_app
import logging

from .api.router import router
from .core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PreciAgro Diagnosis & Recommendation Engine (DRE)",
    description=(
        "Foundational agricultural intelligence engine that transforms observations "
        "from upstream engines into safe, explainable, context-aware agricultural action plans."
    ),
    version=settings.VERSION,
)

app.include_router(router)

# Prometheus metrics
if settings.ENABLE_PROMETHEUS:
    app.mount("/metrics", make_asgi_app())


@app.get("/")
def root():
    """Root info endpoint."""
    return {
        "service": "Diagnosis & Recommendation Engine",
        "status": "operational",
        "version": settings.VERSION,
        "description": (
            "Transforms observations into safe, explainable, context-aware "
            "agricultural action plans"
        ),
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "preciagro.packages.engines.diagnosis_recommendation.app.main:app",
        host="0.0.0.0",
        port=8106,
        reload=settings.DEBUG,
    )

