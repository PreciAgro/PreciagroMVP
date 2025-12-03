"""Configuration for Conversational/NLP Engine."""

from __future__ import annotations

import os
from typing import List

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


class Settings(BaseSettings):
    """Configuration settings for the conversational engine."""

    model_config = ConfigDict(env_file=".env", extra="allow")

    environment: str = os.getenv("ENVIRONMENT", "local")
    debug: bool = _as_bool(os.getenv("DEBUG"), False)
    debug_mode: bool = _as_bool(os.getenv("DEBUG_MODE"), False)

    # Networking / versioning
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8103"))
    engine_api_version: str = os.getenv("ENGINE_API_VERSION", "v1")
    router_version: str = os.getenv("ROUTER_VERSION", "router-v1")
    intent_schema_version: str = os.getenv("INTENT_SCHEMA_VERSION", "intent-v1")
    response_schema_version: str = os.getenv("RESPONSE_SCHEMA_VERSION", "response-v1")

    # Security / auth
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "")
    inbound_api_key: str = os.getenv("CONVERSATIONAL_API_KEY", "")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")
    jwt_pubkey: str = os.getenv("JWT_PUBKEY", "")
    allowed_origins: List[str] = (
        os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
    )

    # Session cache / retention
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
    session_history_turns: int = int(os.getenv("SESSION_HISTORY_TURNS", "6"))
    session_retention_hours: int = int(os.getenv("SESSION_RETENTION_HOURS", "24"))
    conversation_history_enabled: bool = _as_bool(os.getenv("CONVERSATION_HISTORY_ENABLED"), True)

    # AgroLLM endpoints
    agrollm_backend: str = os.getenv("AGROLLM_BACKEND", "stub")
    agrollm_generate_url: str = os.getenv("AGROLLM_GENERATE_URL", "")
    agrollm_classify_url: str = os.getenv("AGROLLM_CLASSIFY_URL", "")
    agrollm_api_key: str = os.getenv("AGROLLM_API_KEY", "")
    agrollm_timeout_seconds: float = float(os.getenv("AGROLLM_TIMEOUT_SECONDS", "15.0"))
    response_system_prompt: str = os.getenv("CONVERSATION_SYSTEM_PROMPT", "")
    flag_force_rule_based_mode: bool = _as_bool(os.getenv("FLAG_FORCE_RULE_BASED_MODE"), False)

    # Engine endpoints (optional; stubs used when absent)
    geo_context_url: str = os.getenv("GEO_CONTEXT_URL", "")
    temporal_logic_url: str = os.getenv("TEMPORAL_LOGIC_URL", "")
    crop_intelligence_url: str = os.getenv("CROP_INTELLIGENCE_URL", "")
    inventory_url: str = os.getenv("INVENTORY_URL", "")
    image_analysis_url: str = os.getenv("IMAGE_ANALYSIS_URL", "")
    flag_enable_geo_engine: bool = _as_bool(os.getenv("FLAG_ENABLE_GEO_ENGINE"), True)
    flag_enable_temporal_engine: bool = _as_bool(os.getenv("FLAG_ENABLE_TEMPORAL_ENGINE"), True)
    flag_enable_image_engine: bool = _as_bool(os.getenv("FLAG_ENABLE_IMAGE_ENGINE"), True)

    # RAG config / feature flag
    rag_enabled: bool = _as_bool(
        os.getenv("FLAG_ENABLE_RAG", os.getenv("RAG_ENABLED", "false")), False
    )
    rag_backend: str = os.getenv("RAG_BACKEND", "qdrant")
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    rag_index_path: str = os.getenv("RAG_INDEX_PATH", "")
    rag_embedder_model: str = os.getenv("RAG_EMBEDDER_MODEL", "sentence-transformers/all-mpnet-base-v2")
    qdrant_host: str = os.getenv("QDRANT_HOST", ":memory:")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "conversational_rag")

    # Timeouts / retries
    engine_timeout_seconds: float = float(os.getenv("ENGINE_TIMEOUT_SECONDS", "8.0"))
    router_fanout_timeout_seconds: float = float(
        os.getenv("ROUTER_FANOUT_TIMEOUT_SECONDS", "6.0")
    )
    engine_retry_attempts: int = int(os.getenv("ENGINE_RETRY_ATTEMPTS", "2"))
    engine_retry_backoff_seconds: float = float(os.getenv("ENGINE_RETRY_BACKOFF_SECONDS", "0.5"))

    # Rate limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    tenant_rate_limit_per_minute: int = int(os.getenv("TENANT_RATE_LIMIT_PER_MINUTE", "600"))

    # Input / attachment policies
    max_message_length: int = int(os.getenv("MAX_MESSAGE_LENGTH", "12000"))
    max_attachments: int = int(os.getenv("MAX_ATTACHMENTS", "5"))
    max_attachment_bytes: int = int(os.getenv("MAX_ATTACHMENT_BYTES", str(5 * 1024 * 1024)))
    allowed_attachment_mime_types: List[str] = [
        mime.strip().lower()
        for mime in os.getenv("ALLOWED_ATTACHMENT_MIME_TYPES", "image/jpeg,image/png").split(",")
        if mime.strip()
    ]

    # Logging / privacy
    conversation_log_path: str = os.getenv("CONVERSATION_LOG_PATH", "reports/conversation_turns.jsonl")
    log_retention_days: int = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    anonymize_logs: bool = _as_bool(os.getenv("ANONYMIZE_LOGS"), False)


settings = Settings()
