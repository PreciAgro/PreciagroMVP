"""Configuration for Feedback & Learning Engine."""

from typing import Optional, List
from pydantic_settings import BaseSettings


class FLESettings(BaseSettings):
    """Settings for Feedback & Learning Engine.
    
    FLE is a learning observer engine that:
    - Captures feedback from upstream engines
    - Validates, weights, and translates signals
    - Routes learning signals to downstream engines
    
    FLE never influences real-time decisions or calls models directly.
    """
    
    # Service configuration
    SERVICE_NAME: str = "feedback-learning"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Engine boundaries
    MAX_FEEDBACK_PER_RECOMMENDATION: int = 10
    FEEDBACK_RETENTION_DAYS: int = 365
    DUPLICATE_WINDOW_HOURS: int = 24
    CONTRADICTION_WINDOW_DAYS: int = 7
    
    # Weighting formula parameters
    BASE_CONFIDENCE: float = 0.5
    FARMER_EXPERIENCE_WEIGHT: float = 0.2
    HISTORICAL_ACCURACY_WEIGHT: float = 0.2
    MODEL_CONFIDENCE_WEIGHT: float = 0.3
    ENVIRONMENTAL_STABILITY_WEIGHT: float = 0.3
    
    # Experience level thresholds
    NOVICE_EXPERIENCE_FACTOR: float = 0.5
    INTERMEDIATE_EXPERIENCE_FACTOR: float = 0.8
    EXPERT_EXPERIENCE_FACTOR: float = 1.0
    
    # Signal routing
    SIGNAL_BATCH_SIZE: int = 100
    SIGNAL_ROUTING_INTERVAL_SECONDS: int = 60
    
    # Redis Streams configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_PREFIX: str = "fle:"
    REDIS_DEAD_LETTER_STREAM: str = "fle:dead_letter"
    REDIS_MAX_STREAM_LENGTH: int = 10000
    
    # Consumer streams per engine
    STREAM_EVALUATION: str = "fle:signals:evaluation"
    STREAM_MODEL_ORCHESTRATION: str = "fle:signals:model_orchestration"
    STREAM_PIE: str = "fle:signals:pie"
    STREAM_HITL: str = "fle:signals:hitl"
    
    # Celery configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # PostgreSQL configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro_fle"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Validation thresholds
    MIN_FEEDBACK_WEIGHT: float = 0.1
    FLAG_THRESHOLD_WEIGHT: float = 0.3
    NOISE_THRESHOLD_RATING_VARIANCE: float = 2.0
    
    # Region handling
    SUPPORTED_REGIONS: List[str] = ["ZW", "ZA", "KE", "NG", "GH"]
    CROSS_REGION_PROPAGATION: bool = False
    
    # Observability
    ENABLE_PROMETHEUS: bool = False
    LOG_LEVEL: str = "INFO"
    ENABLE_AUDIT_LOGGING: bool = True
    
    # External engine URLs (for health checks only, FLE receives via contracts)
    TRUST_ENGINE_URL: Optional[str] = None
    DIAGNOSIS_ENGINE_URL: Optional[str] = None
    
    class Config:
        env_prefix = "FLE_"
        case_sensitive = False


settings = FLESettings()
