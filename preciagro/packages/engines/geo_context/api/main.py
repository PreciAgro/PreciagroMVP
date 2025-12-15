"""FastAPI application for the Geo Context Engine."""

from __future__ import annotations

import os
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from ..config import settings
from ..routers.geocontext import router as geocontext_router
from ..telemetry.metrics import MetricsCollector


def create_app() -> FastAPI:
    """Application factory so tests and scripts share setup."""
    app = FastAPI(
        title="Geo Context Engine",
        version="1.0.0",
        description="Field context resolution service for PreciAgro",
        docs_url="/docs" if os.getenv("DEBUG", "false").lower() == "true" else None,
        redoc_url="/redoc" if os.getenv("DEBUG", "false").lower() == "true" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[host.strip() for host in allowed_hosts]
    )

    metrics = MetricsCollector()

    @app.middleware("http")
    async def record_metrics(
        request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        endpoint = request.url.path
        metrics.record_request(endpoint, "started")

        with metrics.time_request(endpoint):
            try:
                response = await call_next(request)
                metrics.record_request(endpoint, str(response.status_code))
                return response
            except Exception:
                metrics.record_request(endpoint, "error")
                raise

    app.include_router(geocontext_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "geo-context"}

    app.mount("/metrics", make_asgi_app())

    return app


app = create_app()


@app.get("/", tags=["system"])
async def root() -> JSONResponse:
    payload = {
        "engine": "geo_context",
        "version": app.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database_url": (settings.DATABASE_URL.split("@")[-1] if settings.DATABASE_URL else None),
    }
    return JSONResponse(payload)
