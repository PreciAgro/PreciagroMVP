"""Configuration for Conversational/NLP Engine."""

from __future__ import annotations

import os
from typing import List

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the conversational engine."""

    model_config = ConfigDict(env_file=".env", extra="allow")

    environment: str = os.getenv("ENVIRONMENT", "local")
    debug: bool = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

    # Networking
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8103"))

    # Redis session cache
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

    # AgroLLM endpoints
    agrollm_generate_url: str = os.getenv("AGROLLM_GENERATE_URL", "")
    agrollm_classify_url: str = os.getenv("AGROLLM_CLASSIFY_URL", "")
    agrollm_api_key: str = os.getenv("AGROLLM_API_KEY", "")
    agrollm_timeout_seconds: float = float(os.getenv("AGROLLM_TIMEOUT_SECONDS", "15.0"))

    # Engine endpoints (optional; stubs used when absent)
    geo_context_url: str = os.getenv("GEO_CONTEXT_URL", "")
    temporal_logic_url: str = os.getenv("TEMPORAL_LOGIC_URL", "")
    crop_intelligence_url: str = os.getenv("CROP_INTELLIGENCE_URL", "")
    inventory_url: str = os.getenv("INVENTORY_URL", "")
    image_analysis_url: str = os.getenv("IMAGE_ANALYSIS_URL", "")

    # RAG config
    rag_enabled: bool = os.getenv("RAG_ENABLED", "false").lower() in ("1", "true", "yes")
    rag_backend: str = os.getenv("RAG_BACKEND", "qdrant")
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    rag_index_path: str = os.getenv("RAG_INDEX_PATH", "")
    rag_embedder_model: str = os.getenv("RAG_EMBEDDER_MODEL", "sentence-transformers/all-mpnet-base-v2")
    qdrant_host: str = os.getenv("QDRANT_HOST", ":memory:")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "conversational_rag")

    # Internal auth between engines (optional API key)
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "")

    # Inbound auth for this engine (optional)
    inbound_api_key: str = os.getenv("CONVERSATIONAL_API_KEY", "")

    # Security / auth
    jwt_pubkey: str = os.getenv("JWT_PUBKEY", "")
    allowed_origins: List[str] = (
        os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
    )

    # Timeouts
    engine_timeout_seconds: float = float(os.getenv("ENGINE_TIMEOUT_SECONDS", "8.0"))
    router_fanout_timeout_seconds: float = float(
        os.getenv("ROUTER_FANOUT_TIMEOUT_SECONDS", "6.0")
    )
    engine_retry_attempts: int = int(os.getenv("ENGINE_RETRY_ATTEMPTS", "2"))
    engine_retry_backoff_seconds: float = float(os.getenv("ENGINE_RETRY_BACKOFF_SECONDS", "0.5"))

    # Rate limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))


settings = Settings()
