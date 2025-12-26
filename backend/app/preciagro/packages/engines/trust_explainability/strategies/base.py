"""Base Explainer Interface.

Abstract base class for all explanation strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..contracts.v1.schemas import EvidenceItem, ExplanationArtifact
from ..contracts.v1.enums import ExplanationLevel, ExplanationStrategy


class BaseExplainer(ABC):
    """Abstract base class for explanation strategies.

    All explanation strategies must implement this interface
    to ensure consistent behavior across CV, tabular, rule, and LLM explainers.
    """

    @property
    @abstractmethod
    def strategy_type(self) -> ExplanationStrategy:
        """Return the strategy type enum value."""
        pass

    @abstractmethod
    def explain(
        self,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any],
        level: ExplanationLevel = ExplanationLevel.FARMER,
        language: str = "en",
    ) -> ExplanationArtifact:
        """Generate an explanation artifact.

        Args:
            evidence: List of evidence items supporting the decision
            model_output: Model output dictionary to explain
            level: Target audience level
            language: Output language code

        Returns:
            ExplanationArtifact with generated explanation
        """
        pass

    @abstractmethod
    def supports(self, model_type: str) -> bool:
        """Check if this strategy supports the given model type.

        Args:
            model_type: Type of model (e.g., "cv", "tabular", "llm")

        Returns:
            True if this strategy can explain this model type
        """
        pass

    def generate_farmer_summary(
        self, model_output: Dict[str, Any], evidence: List[EvidenceItem]
    ) -> str:
        """Generate a one-line farmer-friendly summary.

        Default implementation - subclasses can override for
        strategy-specific summaries.

        Args:
            model_output: Model output dictionary
            evidence: Supporting evidence

        Returns:
            One-line summary string
        """
        # Extract key information
        diagnosis = model_output.get(
            "diagnosis", model_output.get("prediction", model_output.get("label", "Unknown issue"))
        )
        confidence = model_output.get("confidence", 0.0)

        # Format confidence as percentage
        conf_pct = int(confidence * 100)

        # Simple templates based on confidence
        if conf_pct >= 80:
            return f"This appears to be {diagnosis} (high confidence: {conf_pct}%)."
        elif conf_pct >= 50:
            return f"This may be {diagnosis} (moderate confidence: {conf_pct}%)."
        else:
            return f"Possible {diagnosis}, but confidence is low ({conf_pct}%). Consider getting a second opinion."

    def get_cited_evidence_ids(self, evidence: List[EvidenceItem]) -> List[str]:
        """Extract evidence IDs for citation.

        Args:
            evidence: List of evidence items

        Returns:
            List of evidence IDs
        """
        return [ev.id for ev in evidence]
