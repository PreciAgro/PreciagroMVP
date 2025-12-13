"""Enumerations for Trust & Explainability Engine."""

from enum import Enum


class ExplanationLevel(str, Enum):
    """Target audience level for explanations."""
    
    FARMER = "farmer"       # Short, actionable, plain language
    EXPERT = "expert"       # Detailed reasoning and evidence
    AUDITOR = "auditor"     # Full machine-readable trace


class UncertaintyType(str, Enum):
    """Type of uncertainty in predictions."""
    
    EPISTEMIC = "epistemic"     # Reducible - lack of knowledge/data
    ALEATORIC = "aleatoric"     # Irreducible - inherent randomness
    MIXED = "mixed"             # Combination of both


class SafetyStatus(str, Enum):
    """Safety gate validation status."""
    
    PASSED = "passed"       # All checks passed
    WARNING = "warning"     # Minor issues, can proceed with caution
    BLOCKED = "blocked"     # Critical issues, action blocked


class EvidenceType(str, Enum):
    """Type of evidence supporting a decision."""
    
    IMAGE = "image"                 # Crop/field image
    SENSOR = "sensor"               # IoT sensor reading
    TEXT = "text"                   # Farmer description
    MODEL_OUTPUT = "model_output"   # Output from another model
    RULE = "rule"                   # Rule/knowledge base
    WEATHER = "weather"             # Weather data
    HISTORICAL = "historical"       # Historical records
    EXPERT = "expert"               # Expert knowledge


class ExplanationStrategy(str, Enum):
    """Strategy used to generate explanation."""
    
    CV = "cv"                       # Computer vision (Grad-CAM, etc.)
    TABULAR = "tabular"             # Tabular ML (SHAP, etc.)
    RULE = "rule"                   # Rule-based reasoning
    LLM = "llm"                     # LLM summarization
    EXAMPLE = "example"             # Example-based retrieval
    COUNTERFACTUAL = "counterfactual"  # Counterfactual reasoning
    HYBRID = "hybrid"               # Multiple strategies combined


class ViolationSeverity(str, Enum):
    """Severity of safety/compliance violation."""
    
    BLOCKING = "blocking"   # Must reject - action cannot proceed
    WARNING = "warning"     # Can proceed with explicit warning
    INFO = "info"           # Informational only
