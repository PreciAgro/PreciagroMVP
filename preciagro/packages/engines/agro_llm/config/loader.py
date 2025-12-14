"""Configuration Loader - YAML-based configuration system."""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelProviderConfig(BaseModel):
    """Model provider configuration."""
    
    mode: str = Field(default="pretrained", description="LLM mode: pretrained, self_hosted, future_finetuned")
    model_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1)


class SafetyRulesConfig(BaseModel):
    """Safety rules configuration."""
    
    banned_chemicals: list[str] = Field(default_factory=list)
    strict_mode: bool = Field(default=True)
    require_warnings_for_high_severity: bool = Field(default=True)


class RegionRulesConfig(BaseModel):
    """Region-specific rules configuration."""
    
    default_region: str = Field(default="unknown")
    rules_directory: Optional[str] = None
    compliance_matrix_file: Optional[str] = None


class OrchestratorConfig(BaseModel):
    """Orchestrator configuration."""
    
    enabled: bool = Field(default=False)
    endpoint: Optional[str] = None
    timeout_seconds: int = Field(default=30)


class FeatureFlagsConfig(BaseModel):
    """Feature flags configuration."""
    
    use_pretrained: bool = Field(default=True)
    use_finetuned: bool = Field(default=False)
    use_local: bool = Field(default=True)
    enable_rag: bool = Field(default=True)
    enable_kg: bool = Field(default=True)
    enable_feedback: bool = Field(default=True)


class ThresholdsConfig(BaseModel):
    """Confidence thresholds configuration."""
    
    low_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    high_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    human_review_required: float = Field(default=0.5, ge=0.0, le=1.0)


class TemporalSafetyConfig(BaseModel):
    """Temporal safety configuration."""
    
    enabled: bool = Field(default=True)
    phi_rules: list[Dict[str, Any]] = Field(default_factory=list)
    crop_stage_rules: list[Dict[str, Any]] = Field(default_factory=list)


class FallbackConfig(BaseModel):
    """Fallback configuration."""
    
    enabled: bool = Field(default=True)
    mode: str = Field(default="basic")  # basic, safe_default
    activate_on_llm_failure: bool = Field(default=True)
    activate_on_rag_failure: bool = Field(default=False)
    activate_on_api_failure: bool = Field(default=False)


class EventEmissionConfig(BaseModel):
    """Event emission configuration."""
    
    enabled: bool = Field(default=True)
    feedback_endpoint: Optional[str] = None
    event_bus_endpoint: Optional[str] = None


class AgroLLMConfig(BaseModel):
    """Main AgroLLM configuration."""
    
    model_provider: ModelProviderConfig = Field(default_factory=ModelProviderConfig)
    safety_rules: SafetyRulesConfig = Field(default_factory=SafetyRulesConfig)
    region_rules: RegionRulesConfig = Field(default_factory=RegionRulesConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    feature_flags: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    temporal_safety: TemporalSafetyConfig = Field(default_factory=TemporalSafetyConfig)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    event_emission: EventEmissionConfig = Field(default_factory=EventEmissionConfig)
    
    # Engine endpoints
    image_analysis_endpoint: Optional[str] = None
    geo_context_endpoint: Optional[str] = None
    temporal_logic_endpoint: Optional[str] = None
    crop_intelligence_endpoint: Optional[str] = None
    data_integration_endpoint: Optional[str] = None
    inventory_endpoint: Optional[str] = None
    security_access_endpoint: Optional[str] = None
    
    # RAG/KG settings
    rag_endpoint: Optional[str] = None
    kg_endpoint: Optional[str] = None
    
    # Storage
    feedback_storage_endpoint: Optional[str] = None
    
    # Region compliance matrix (loaded separately)
    region_compliance: Dict[str, Any] = Field(default_factory=dict)


class ConfigLoader:
    """Loader for YAML configuration files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config loader.
        
        Args:
            config_path: Path to YAML config file
        """
        self.config_path = Path(config_path) if config_path else Path(__file__).parent / "config.yaml"
        self.config: Optional[AgroLLMConfig] = None
    
    def load(self) -> AgroLLMConfig:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # Load region compliance matrix if specified
                region_compliance = {}
                if "region_rules" in data and "compliance_matrix_file" in data["region_rules"]:
                    compliance_file = Path(self.config_path.parent) / data["region_rules"]["compliance_matrix_file"]
                    if compliance_file.exists():
                        try:
                            with open(compliance_file, 'r', encoding='utf-8') as cf:
                                region_compliance = yaml.safe_load(cf) or {}
                            logger.info(f"Loaded region compliance matrix from {compliance_file}")
                        except Exception as e:
                            logger.warning(f"Error loading region compliance: {e}")
                
                # Add region compliance to config data
                data["region_compliance"] = region_compliance
                
                self.config = AgroLLMConfig(**data)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Error loading config from {self.config_path}: {e}, using defaults")
                self.config = AgroLLMConfig()
        else:
            logger.info(f"Config file not found at {self.config_path}, using defaults")
            self.config = AgroLLMConfig()
        
        return self.config
    
    def get_config(self) -> AgroLLMConfig:
        """Get current configuration."""
        if self.config is None:
            return self.load()
        return self.config

