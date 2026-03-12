"""Contracts package - defines input/output data structures for FLE."""

from .upstream import (
    ExplicitFeedbackInput,
    ImplicitFeedbackInput,
    OutcomeFeedbackInput,
    RecommendationContext,
    ReasoningTraceRef,
    FarmerProfileContext,
    OutcomeTimingContext,
    FeedbackType,
)

from .downstream import (
    LearningSignalOutput,
    FlaggedFeedbackOutput,
    AuditExportOutput,
    SignalType,
    FlagReason,
)

__all__ = [
    # Upstream
    "ExplicitFeedbackInput",
    "ImplicitFeedbackInput",
    "OutcomeFeedbackInput",
    "RecommendationContext",
    "ReasoningTraceRef",
    "FarmerProfileContext",
    "OutcomeTimingContext",
    "FeedbackType",
    # Downstream
    "LearningSignalOutput",
    "FlaggedFeedbackOutput",
    "AuditExportOutput",
    "SignalType",
    "FlagReason",
]
