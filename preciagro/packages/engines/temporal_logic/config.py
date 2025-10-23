"""Configuration management for Temporal Logic Engine."""
import os
from pydantic_settings import BaseSettings
from typing import Optional, List


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

    class Config:
        env_file = ".env"
        case_sensitive = False


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
