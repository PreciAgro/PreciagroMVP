"""Configuration management for Temporal Logic Engine."""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for Temporal Logic Engine."""

    database_url: Optional[str] = os.getenv("DATABASE_URL")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_pubkey: Optional[str] = os.getenv("SERVICE_JWT_PUBLIC_KEY")
    whatsapp_token: Optional[str] = os.getenv("WHATSAPP_TOKEN")
    whatsapp_phone_id: Optional[str] = os.getenv("WHATSAPP_PHONE_ID")
    twilio_sid: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from: Optional[str] = os.getenv("TWILIO_FROM")
    max_notifications_per_day: int = int(os.getenv("MAX_NOTIFS_PER_DAY", "5"))
    digest_hour_local: int = int(os.getenv("DIGEST_HOUR_LOCAL", "19"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # FastAPI app config
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    enable_worker: bool = os.getenv("ENABLE_WORKER", "false").lower() == "true"
    cors_origins: List[str] = []
    allowed_hosts: List[str] = ["*"]
    arq_job_timeout: int = int(os.getenv("ARQ_JOB_TIMEOUT", "60"))
    arq_max_retries: int = int(os.getenv("ARQ_MAX_RETRIES", "3"))
    arq_max_jobs: int = int(os.getenv("ARQ_MAX_JOBS", "10"))
    arq_retry_jobs: bool = os.getenv("ARQ_RETRY_JOBS", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    arq_max_tries: int = int(os.getenv("ARQ_MAX_TRIES", "3"))

    class Config:
        # Only load .env when DEV flag is set to avoid parsing shell-style
        # .env files that may contain shell-specific syntax (e.g. PowerShell
        # lines like "$env:FOO = \"bar\""). This mirrors other engines
        # and prevents Pydantic from treating unexpected keys as input.
        env_file = (
            ".env" if os.getenv("DEV", "").lower() in (
                "1", "true", "yes") else None
        )
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env file


# Create global settings instance
config = Settings()

# Legacy module-level constants for backwards compatibility
DATABASE_URL = config.database_url
REDIS_URL = config.redis_url
JWT_PUBKEY = config.jwt_pubkey
WHATSAPP_TOKEN = config.whatsapp_token
WHATSAPP_PHONE_ID = config.whatsapp_phone_id
TWILIO_SID = config.twilio_sid
TWILIO_TOKEN = config.twilio_token
TWILIO_FROM = config.twilio_from
MAX_NOTIFICATIONS_PER_DAY = config.max_notifications_per_day
DIGEST_HOUR_LOCAL = config.digest_hour_local
ARQ_JOB_TIMEOUT = config.arq_job_timeout
ARQ_MAX_RETRIES = config.arq_max_retries
ARQ_MAX_JOBS = config.arq_max_jobs
ARQ_RETRY_JOBS = config.arq_retry_jobs
ARQ_MAX_TRIES = config.arq_max_tries
