from fastapi import FastAPI
from prometheus_client import make_asgi_app
from .api.router import router as cie_router, crop_router
from .core.config import settings
from preciagro.packages.shared.logging import configure_logging

configure_logging(debug=settings.DEBUG, service_name="crop-intelligence")

app = FastAPI(
    title="PreciAgro Crop Intelligence Engine (MVP)",
    description="Explainable agronomic engine delivering accurate, trustable, region-relevant recommendations",
    version="0.1.0"
)

app.include_router(cie_router)
app.include_router(crop_router)
if settings.ENABLE_PROMETHEUS:
    app.mount("/metrics", make_asgi_app())


@app.get("/")
def root():
    """Root info endpoint."""
    return {
        "service": "Crop Intelligence Engine",
        "status": "operational",
        "version": "0.1.0"
    }

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
