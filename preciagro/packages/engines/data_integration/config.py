from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Use a .env file in development. Secrets must not be committed to git.
    """

    OPENWEATHER_API_KEY: str | None = Field(
        None, description="OpenWeather API key")
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro", description="Async DB URL")
    REDIS_URL: str = Field("redis://localhost:6379/0",
                           description="Redis connection URL")
    INGEST_RATE_LIMIT_QPS: int = Field(5, description="Default QPS per source")

    class Config:
        # Load only from real environment variables in production.
        # Do not read a .env file here to avoid committing secrets or
        # accidentally loading local files in CI. Developers may still use
        # their own env var loading when running locally.
        env_file = None


settings = Settings()
