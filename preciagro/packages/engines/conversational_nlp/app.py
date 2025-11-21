"""FastAPI application for the Conversational/NLP Engine."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app

from .api.routes import router as api_router
from .core.config import settings
from .services.orchestrator import ConversationOrchestrator
from .services.session import SessionStore
from .services.tracing import init_tracer


logger = logging.getLogger(__name__)

session_store = SessionStore(redis_url=settings.redis_url, ttl_seconds=settings.session_ttl_seconds)
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
        version="0.1.0",
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
        }

    return app


app = create_app()
