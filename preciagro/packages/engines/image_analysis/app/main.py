"""ASGI entrypoint for the Image Analysis Engine."""

from __future__ import annotations

from fastapi import FastAPI

try:
    from prometheus_client import make_asgi_app
except ImportError:  # pragma: no cover - optional dependency
    make_asgi_app = None

from .api import router as api_router
from .core import settings

tags_metadata = [
    {
        "name": "image-analysis",
        "description": "Operations for analyzing single crop images (MVP stub).",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Pretrained-first image analysis engine that ingests crop photos, "
        "runs quality gates, classifier heads, optional segmentation/counting, "
        "and returns the standard JSON contract for downstream engines."
    ),
    version=settings.APP_VERSION,
    contact={"name": "PreciAgro Engineering", "email": settings.CONTACT_EMAIL},
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    openapi_tags=tags_metadata,
)

app.include_router(api_router)

if settings.ENABLE_PROMETHEUS and make_asgi_app is not None:
    app.mount("/metrics", make_asgi_app())


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Simple landing endpoint for quick smoke checks."""

    return {
        "service": settings.APP_NAME,
        "status": "ok",
        "docs": settings.DOCS_URL,
        "openapi": settings.OPENAPI_URL,
    }
