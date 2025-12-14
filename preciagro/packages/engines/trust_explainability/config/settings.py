"""Configuration settings for Trust & Explainability Engine."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class TEESettings(BaseSettings):
    """Trust & Explainability Engine configuration."""
    
    # Confidence thresholds
    confidence_threshold_high: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Threshold for high confidence classification"
    )
    confidence_threshold_medium: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Threshold for medium confidence classification"
    )
    confidence_threshold_action: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Minimum confidence to recommend action"
    )
    
    # Safety gate settings
    safety_gate_enabled: bool = Field(
        default=True, description="Enable safety gate validation"
    )
    safety_gate_strict: bool = Field(
        default=True, description="Strict mode blocks on warnings"
    )
    
    # Explanation settings
    enable_shap: bool = Field(
        default=True, description="Enable SHAP-based explanations"
    )
    enable_gradcam: bool = Field(
        default=True, description="Enable Grad-CAM saliency maps"
    )
    enable_llm_summary: bool = Field(
        default=True, description="Enable LLM-based summaries"
    )
    
    # Default explanation language
    default_language: str = Field(
        default="en", description="Default explanation language"
    )
    
    # Trace storage
    trace_storage_type: str = Field(
        default="memory", description="Trace storage type (memory, sqlite, postgres)"
    )
    trace_storage_path: str = Field(
        default="./traces", description="Path for file-based trace storage"
    )
    max_trace_age_days: int = Field(
        default=90, description="Maximum trace retention in days"
    )
    
    # Performance
    max_evidence_items: int = Field(
        default=50, description="Maximum evidence items per trace"
    )
    explanation_timeout_seconds: float = Field(
        default=10.0, description="Timeout for explanation generation"
    )
    
    # Banned chemicals list (for safety gate)
    banned_chemicals: List[str] = Field(
        default_factory=lambda: [
            "DDT", "Paraquat", "Endosulfan", "Chlordane", "Aldrin", "Dieldrin"
        ],
        description="List of banned chemicals"
    )
    
    # API settings
    api_prefix: str = Field(
        default="/api/v1", description="API route prefix"
    )
    api_port: int = Field(
        default=8008, description="API server port"
    )
    
    # Feature flags
    feature_counterfactual: bool = Field(
        default=False, description="Enable counterfactual explanations (Phase 2)"
    )
    feature_example_based: bool = Field(
        default=False, description="Enable example-based explanations (Phase 2)"
    )
    feature_audit_signatures: bool = Field(
        default=False, description="Enable cryptographic signatures (Phase 2)"
    )
    
    # Integration URLs
    image_analysis_url: Optional[str] = Field(
        default=None, description="Image Analysis Engine URL"
    )
    feedback_engine_url: Optional[str] = Field(
        default=None, description="Feedback & Learning Engine URL"
    )
    
    class Config:
        env_prefix = "TEE_"
        env_file = ".env"
        extra = "ignore"


# Singleton instance
_settings: Optional[TEESettings] = None


def get_settings() -> TEESettings:
    """Get singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = TEESettings()
    return _settings
