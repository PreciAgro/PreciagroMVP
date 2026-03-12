"""Configuration for Geo Context Engine."""

import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Geo Context Engine settings."""

    model_config = ConfigDict(env_file=".env", extra="allow")  # Allow extra fields for flexibility

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5432/preciagro"
    )

    # PostGIS extension
    ENABLE_POSTGIS: bool = os.getenv("ENABLE_POSTGIS", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # External services
    WEATHER_API_URL: str = os.getenv("WEATHER_API_URL", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")

    SOIL_API_URL: str = os.getenv("SOIL_API_URL", "")
    SOIL_API_KEY: str = os.getenv("SOIL_API_KEY", "")

    # JWT Configuration
    JWT_PUBKEY: str = os.getenv("JWT_PUBKEY", "")

    # Cache settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour

    # Spatial resolution settings
    DEFAULT_GRID_SIZE: float = 0.001  # ~100m resolution
    MAX_POLYGON_AREA: float = float(os.getenv("MAX_POLYGON_AREA", "20000"))  # hectares


settings = Settings()
