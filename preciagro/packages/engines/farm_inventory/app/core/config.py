"""Configuration for Farm Inventory Engine."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for Farm Inventory Engine."""
    
    ENV: str = "dev"
    ENGINE_NAME: str = "farm_inventory"
    DATABASE_URL: str = "sqlite:///./farm_inventory.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    AUTO_CREATE_SCHEMA: bool = True
    SERVICE_AUTH_TOKEN: str = ""
    API_AUTH_TOKEN: str = ""
    ENABLE_PROMETHEUS: bool = True
    DEBUG: bool = False
    
    # Offline-first settings
    OFFLINE_MODE: bool = False
    SYNC_ENABLED: bool = True
    SYNC_INTERVAL_SECONDS: int = 300  # 5 minutes
    
    # External service URLs
    CROP_INTELLIGENCE_URL: str = "http://localhost:8104"
    TEMPORAL_LOGIC_URL: str = "http://localhost:8100"
    DIAGNOSIS_RECOMMENDATION_URL: str = ""
    AGROLLM_URL: str = ""
    SECURITY_ACCESS_URL: str = ""
    
    # Alert thresholds
    LOW_STOCK_THRESHOLD: float = 0.2  # 20% of typical usage
    CRITICAL_STOCK_THRESHOLD: float = 0.1  # 10% of typical usage
    EXPIRY_WARNING_DAYS: int = 30  # Warn 30 days before expiry
    
    # Depletion prediction
    DEFAULT_USAGE_RATE_DAYS: int = 7  # Default lookback for usage rate calculation
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

