"""Main FastAPI application for Farm Inventory Engine."""

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from .api.router import router
from .core.config import settings
from preciagro.packages.shared.logging import configure_logging

configure_logging(debug=settings.DEBUG, service_name="farm-inventory")

app = FastAPI(
    title="PreciAgro Farm Inventory Engine (MVP)",
    description=(
        "Decision constraint engine that ensures all AI advice is realistic, "
        "affordable, and executable. Tracks, validates, predicts, and reasons "
        "over farm inputs."
    ),
    version="1.0.0",
)

app.include_router(router)

if settings.ENABLE_PROMETHEUS:
    app.mount("/metrics", make_asgi_app())


@app.get("/")
def root():
    """Root info endpoint."""
    return {
        "service": "Farm Inventory Engine",
        "status": "operational",
        "version": "1.0.0",
        "description": "Decision constraint engine for farm inputs",
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "engine": "farm_inventory"}

