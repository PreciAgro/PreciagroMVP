import os

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Use a .env file in development. Secrets must not be committed to git.
    """

    OPENWEATHER_API_KEY: str | None = Field(
        None, description="OpenWeather API key")
    DATABASE_URL: str = Field(
        default=...,
        description="Async DB URL (required - must be set via environment variable)",
    )
    REDIS_URL: str = Field(
        "redis://localhost:6379/0", description="Redis connection URL"
    )
    INGEST_RATE_LIMIT_QPS: int = Field(5, description="Default QPS per source")

    class Config:
        # By default do not load a .env file (safer for production/CI).
        # For local development set the `DEV` env var to true and the
        # module will load `.env` below before instantiating Settings.
        env_file = (
            ".env" if os.getenv("DEV", "").lower() in (
                "1", "true", "yes") else None
        )
        extra = "ignore"  # Allow extra fields from .env file


settings = Settings()
