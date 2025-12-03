"""FastAPI application for the Conversational/NLP Engine."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app

from .api.routes import router as api_router
from .core.config import settings
from preciagro.packages.shared.logging import configure_logging
from .services.orchestrator import ConversationOrchestrator
from .services.session import SessionStore
from .services.tracing import init_tracer

logger = logging.getLogger(__name__)

configure_logging(debug=settings.debug)

session_store = SessionStore(
    redis_url=settings.redis_url,
    ttl_seconds=settings.session_ttl_seconds,
    max_turns=settings.session_history_turns,
    history_enabled=settings.conversation_history_enabled,
    retention_hours=settings.session_retention_hours,
)
orchestrator = ConversationOrchestrator(session_store=session_store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown for the engine."""
    init_tracer(service_name="conversational-nlp")
    await session_store.connect()
    app.state.orchestrator = orchestrator
    logger.info("Conversational/NLP Engine started")
    try:
        yield
    finally:
        await session_store.close()
        logger.info("Conversational/NLP Engine shutdown complete")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Conversational / NLP Engine",
        version=settings.engine_api_version,
        description="Intent-aware chat engine in front of AgroLLM and internal tools.",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],
    )

    app.include_router(api_router)
    app.mount("/metrics", make_asgi_app())

    @app.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {
            "engine": "conversational-nlp",
            "version": app.version,
            "environment": settings.environment,
            "intent_schema": settings.intent_schema_version,
            "response_schema": settings.response_schema_version,
        }
    
    @app.get("/health", tags=["system"])
    async def health(response: Response) -> dict[str, Any]:
        """Health check that verifies Redis connectivity."""
        status = {"status": "ok", "details": {"redis": "disabled"}}
        
        store = app.state.orchestrator.session_store
        if store.redis:
            try:
                await store.redis.ping()
                status["details"]["redis"] = "connected"
            except Exception:
                status["status"] = "error"
                status["details"]["redis"] = "unreachable"
                response.status_code = 503
        
        return status

    return app


app = create_app()
