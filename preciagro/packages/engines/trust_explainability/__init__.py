"""Trust & Explainability Engine - The moral and technical backbone of PreciAgro.

This engine provides:
- Model-agnostic explanations for CV, tabular, rule-based, and LLM models
- Calibrated confidence scoring with uncertainty quantification
- Pre-action safety gate validation
- Immutable reasoning traces for audits
- Tiered explanations for farmers, experts, and auditors
- Feedback collection and routing

Usage:
    from preciagro.packages.engines.trust_explainability import (
        ExplanationService,
        ExplanationRequest,
        ExplanationResponse,
    )
    
    service = ExplanationService()
    response = await service.explain(request)
"""

from typing import Dict, Any

# Core contracts
from .contracts.v1.schemas import (
    ExplanationRequest,
    ExplanationResponse,
    ReasoningTrace,
    EvidenceItem,
    ExplanationArtifact,
    ConfidenceMetrics,
    SafetyCheckResult,
    SafetyViolation,
    FeedbackPayload,
    ModelInfo,
)
from .contracts.v1.enums import (
    ExplanationLevel,
    UncertaintyType,
    SafetyStatus,
    EvidenceType,
    ExplanationStrategy,
    ViolationSeverity,
)

# Core modules
from .core.evidence_collector import EvidenceCollector
from .core.explanation_router import ExplanationRouter
from .core.confidence_estimator import ConfidenceEstimator
from .core.safety_gate import SafetyGate
from .core.reasoning_trace import ReasoningTraceBuilder, TraceStore, get_trace_store

# Explanation strategies
from .strategies.base import BaseExplainer
from .strategies.cv_explainer import CVExplainer
from .strategies.tabular_explainer import TabularExplainer
from .strategies.rule_explainer import RuleExplainer
from .strategies.llm_summarizer import LLMSummarizer

# Services
from .services.explanation_service import ExplanationService
from .services.trace_service import TraceService
from .services.feedback_service import FeedbackService

# Configuration
from .config.settings import TEESettings, get_settings


# Engine interface functions for compatibility
def run(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run trust explainability engine (sync interface).
    
    Args:
        data: Input data containing model outputs to explain
        
    Returns:
        Dictionary with explanations and trace ID
    """
    import asyncio
    
    # Parse request
    request = ExplanationRequest(
        model_type=data.get("model_type", "tabular"),
        model_id=data.get("model_id", "unknown"),
        model_outputs=data.get("model_outputs", data),
        context=data.get("context", {}),
        language=data.get("language", "en")
    )
    
    # Run explanation
    service = ExplanationService()
    loop = asyncio.new_event_loop()
    try:
        response = loop.run_until_complete(service.explain(request))
    finally:
        loop.close()
    
    return {
        "engine": "trust_explainability",
        "status": "success",
        "trace_id": response.trace_id,
        "farmer_explanation": response.farmer_explanation,
        "confidence": response.confidence,
        "safety_status": response.safety_status.value,
        "safety_warnings": response.safety_warnings,
    }


def status() -> Dict[str, Any]:
    """Get engine status.
    
    Returns:
        Dictionary with engine state information
    """
    settings = get_settings()
    trace_store = get_trace_store()
    
    return {
        "engine": "trust_explainability",
        "state": "ready",
        "version": "1.0.0",
        "implemented": True,
        "trace_count": trace_store.count(),
        "features": {
            "shap_enabled": settings.enable_shap,
            "gradcam_enabled": settings.enable_gradcam,
            "llm_summary_enabled": settings.enable_llm_summary,
            "safety_gate_enabled": settings.safety_gate_enabled,
        }
    }


def explain_prediction(model_output: Dict[str, Any], model_type: str) -> Dict[str, Any]:
    """Generate explanation for a model prediction.
    
    Args:
        model_output: Output from the model
        model_type: Type of model (e.g., 'cv', 'tabular', 'rule')
        
    Returns:
        Explanation including feature importance, reasoning, etc.
    """
    return run({
        "model_type": model_type,
        "model_outputs": model_output,
    })


__all__ = [
    # Main interface
    "run",
    "status", 
    "explain_prediction",
    
    # Services
    "ExplanationService",
    "TraceService",
    "FeedbackService",
    
    # Contracts
    "ExplanationRequest",
    "ExplanationResponse",
    "ReasoningTrace",
    "EvidenceItem",
    "ExplanationArtifact",
    "ConfidenceMetrics",
    "SafetyCheckResult",
    "SafetyViolation",
    "FeedbackPayload",
    "ModelInfo",
    
    # Enums
    "ExplanationLevel",
    "UncertaintyType",
    "SafetyStatus",
    "EvidenceType",
    "ExplanationStrategy",
    "ViolationSeverity",
    
    # Core modules
    "EvidenceCollector",
    "ExplanationRouter",
    "ConfidenceEstimator",
    "SafetyGate",
    "ReasoningTraceBuilder",
    "TraceStore",
    "get_trace_store",
    
    # Strategies
    "BaseExplainer",
    "CVExplainer",
    "TabularExplainer",
    "RuleExplainer",
    "LLMSummarizer",
    
    # Configuration
    "TEESettings",
    "get_settings",
]


