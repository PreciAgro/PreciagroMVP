"""Feedback & Learning Engine - Learning observer for PreciAgro.

This engine captures feedback from upstream engines, validates and weights it,
then routes learning signals to downstream engines for model and system improvement.

FLE is a **learning observer** that:
- Observes feedback (explicit, implicit, outcome)
- Validates feedback quality (duplicate, contradiction, noise detection)
- Weights feedback using a 5-factor formula
- Translates weighted feedback into typed learning signals
- Routes signals to Evaluation, Model Orchestration, and PIE engines

FLE never:
- Generates recommendations
- Calls CV, NLP, or LLM models
- Retrains or fine-tunes models
- Overrides decisions
- Modifies historical intelligence outputs

Usage:
    from preciagro.packages.engines.feedback_learning import (
        FLESettings,
        CaptureService,
        ValidationService,
        WeightingService,
        SignalService,
        RoutingService,
        AuditService,
    )
    
    # Or use the FastAPI app
    from preciagro.packages.engines.feedback_learning.app.main import app
"""

from typing import Dict, Any

# Configuration
from .app.config import FLESettings, settings

# Contracts
from .app.contracts.upstream import (
    ExplicitFeedbackInput,
    ImplicitFeedbackInput,
    OutcomeFeedbackInput,
    RecommendationContext,
    ReasoningTraceRef,
    FarmerProfileContext,
    OutcomeTimingContext,
    FeedbackType,
)
from .app.contracts.downstream import (
    LearningSignalOutput,
    FlaggedFeedbackOutput,
    AuditExportOutput,
    SignalType,
    FlagReason,
    ReviewDecision,
)

# Models
from .app.models.feedback_event import FeedbackEvent
from .app.models.weighted_feedback import WeightedFeedback
from .app.models.learning_signal import LearningSignal
from .app.models.audit_trace import FeedbackAuditTrace, AuditStep

# Services
from .app.services.capture_service import CaptureService
from .app.services.validation_service import ValidationService, ValidationResult
from .app.services.weighting_service import WeightingService, WeightFactors
from .app.services.signal_service import SignalService
from .app.services.routing_service import RoutingService, RoutingResult
from .app.services.audit_service import AuditService


def run(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run feedback learning engine (sync interface).
    
    Args:
        data: Input data containing feedback to process
        
    Returns:
        Dictionary with processing results
    """
    import asyncio
    
    # Determine feedback type
    feedback_type = data.get("feedback_type", "explicit")
    
    # Create input based on type
    if feedback_type == "explicit":
        input_data = ExplicitFeedbackInput(
            recommendation_id=data.get("recommendation_id", ""),
            rating=data.get("rating"),
            feedback_category=data.get("feedback_category", "other"),
            user_id=data.get("user_id", "unknown"),
            region_code=data.get("region_code", "ZW"),
        )
        
        capture = CaptureService()
        
        async def _capture():
            return await capture.capture_explicit_feedback(input_data)
        
        loop = asyncio.new_event_loop()
        try:
            event = loop.run_until_complete(_capture())
        finally:
            loop.close()
        
        return {
            "engine": "feedback_learning",
            "status": "captured",
            "feedback_id": event.feedback_id,
            "feedback_type": feedback_type,
        }
    
    return {
        "engine": "feedback_learning",
        "status": "error",
        "message": f"Unsupported feedback type: {feedback_type}",
    }


def status() -> Dict[str, Any]:
    """Get engine status.
    
    Returns:
        Dictionary with engine state information
    """
    return {
        "engine": "feedback_learning",
        "state": "ready",
        "version": settings.VERSION,
        "implemented": True,
        "features": {
            "explicit_feedback": True,
            "implicit_feedback": True,
            "outcome_feedback": True,
            "validation": True,
            "weighting": True,
            "signal_generation": True,
            "routing": True,
            "audit_traces": True,
        },
        "boundaries": {
            "does": [
                "Observe feedback",
                "Validate quality",
                "Weight signals",
                "Route to engines",
            ],
            "does_not": [
                "Generate recommendations",
                "Call models",
                "Override decisions",
            ],
        },
    }


def collect_feedback(feedback_data: Dict[str, Any]) -> Dict[str, Any]:
    """Collect and store feedback.
    
    Args:
        feedback_data: Feedback data including type, content, ratings, etc.
        
    Returns:
        Feedback collection result
    """
    return run(feedback_data)


def process_feedback_for_learning(feedback_id: str) -> Dict[str, Any]:
    """Process feedback for model learning/improvement.
    
    Args:
        feedback_id: Identifier of the feedback to process
        
    Returns:
        Learning insights and signal information
    """
    # In production, this would trigger the full pipeline
    return {
        "feedback_id": feedback_id,
        "status": "queued",
        "message": "Feedback queued for processing through pipeline",
    }


__all__ = [
    # Main interface
    "run",
    "status",
    "collect_feedback",
    "process_feedback_for_learning",
    
    # Configuration
    "FLESettings",
    "settings",
    
    # Services
    "CaptureService",
    "ValidationService",
    "ValidationResult",
    "WeightingService",
    "WeightFactors",
    "SignalService",
    "RoutingService",
    "RoutingResult",
    "AuditService",
    
    # Upstream contracts
    "ExplicitFeedbackInput",
    "ImplicitFeedbackInput",
    "OutcomeFeedbackInput",
    "RecommendationContext",
    "ReasoningTraceRef",
    "FarmerProfileContext",
    "OutcomeTimingContext",
    "FeedbackType",
    
    # Downstream contracts
    "LearningSignalOutput",
    "FlaggedFeedbackOutput",
    "AuditExportOutput",
    "SignalType",
    "FlagReason",
    "ReviewDecision",
    
    # Models
    "FeedbackEvent",
    "WeightedFeedback",
    "LearningSignal",
    "FeedbackAuditTrace",
    "AuditStep",
]


