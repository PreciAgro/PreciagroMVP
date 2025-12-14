"""Runtime configuration for the Image Analysis Engine."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings with sane defaults for local development."""

    APP_NAME: str = "PreciAgro Image Analysis Engine"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["local", "dev", "qa", "prod"] = "local"
    API_PREFIX: str = "/api/image-analysis"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    CONTACT_EMAIL: str = "engineering@preciagro.com"
    LOG_LEVEL: str = "INFO"
    DEFAULT_REGION: str = "global"
    ENABLE_PROMETHEUS: bool = False
    EXPLAINABILITY_ENABLED: bool = True
    ARTIFACT_STORAGE_DIR: str = "reports/image_analysis/artifacts"
    ARTIFACT_BASE_URL: str = ""
    CHECKPOINT_CACHE_DIR: str = ".cache/image_analysis/checkpoints"
    MIN_CONFIDENCE_HEALTHY: float = 0.55
    UNCERTAIN_NOTE: str = "Prediction confidence is low. Please retake a clear, well-lit photo."
    MAX_BASE64_BYTES: int = 5 * 1024 * 1024
    MAX_BATCH_ITEMS: int = 10
    MAX_DOWNLOAD_BYTES: int = 8 * 1024 * 1024
    DOWNLOAD_TIMEOUT_SECONDS: int = 10
    ALLOWED_IMAGE_HOSTS: list[str] = Field(default_factory=list)
    SIGNED_URL_REQUIRED_PARAMS: list[str] = Field(
        default_factory=lambda: ["signature", "token", "sig"]
    )

    model_config = SettingsConfigDict(
        env_prefix="IMAGE_ANALYSIS_",
        env_file=".env",
        extra="allow",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()


settings = get_settings()
