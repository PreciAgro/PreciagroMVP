"""Configuration for Diagnosis & Recommendation Engine."""

from typing import Optional
from pydantic_settings import BaseSettings


class DRESettings(BaseSettings):
    """Settings for Diagnosis & Recommendation Engine."""
    
    # Service configuration
    SERVICE_NAME: str = "diagnosis-recommendation"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Engine boundaries
    MAX_HYPOTHESES: int = 10
    MIN_CONFIDENCE_THRESHOLD: float = 0.3
    ESCALATION_CONFIDENCE_THRESHOLD: float = 0.4
    
    # Safety and constraints
    ENABLE_SAFETY_VALIDATION: bool = True
    ENABLE_CONSTRAINT_CHECKING: bool = True
    BLOCK_LOW_CONFIDENCE_ACTIONS: bool = True
    
    # Model adapters (future ML integration)
    ENABLE_CV_ADAPTER: bool = False
    ENABLE_NLP_ADAPTER: bool = False
    ENABLE_LLM_ADAPTER: bool = False
    ENABLE_RL_ADAPTER: bool = False
    ENABLE_GRAPH_ADAPTER: bool = False
    
    # Explainability
    ENABLE_REASONING_TRACE: bool = True
    TRACE_RETENTION_HOURS: int = 24
    
    # Performance
    EVIDENCE_GRAPH_TTL_SECONDS: int = 3600
    MAX_PROCESSING_TIME_MS: float = 5000.0
    
    # External services
    GEO_CONTEXT_URL: Optional[str] = None
    TEMPORAL_LOGIC_URL: Optional[str] = None
    CROP_INTELLIGENCE_URL: Optional[str] = None
    INVENTORY_URL: Optional[str] = None
    
    # Observability
    ENABLE_PROMETHEUS: bool = False
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_prefix = "DRE_"
        case_sensitive = False


settings = DRESettings()

