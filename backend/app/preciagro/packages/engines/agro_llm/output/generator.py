"""Structured Output Generator - Enforces strict JSON schema."""

import json
import logging
from typing import Dict, Any, Optional

from ..contracts.v1.schemas import (
    AgroLLMResponse,
    DiagnosisCard,
    RecommendedAction,
    Explainability,
    ResponseFlags,
)

logger = logging.getLogger(__name__)


class StructuredOutputGenerator:
    """Generator for structured JSON output with schema enforcement."""

    def __init__(self, strict_schema: bool = True):
        """Initialize structured output generator.

        Args:
            strict_schema: If True, enforce strict schema validation
        """
        self.strict_schema = strict_schema
        logger.info(f"StructuredOutputGenerator initialized (strict_schema={strict_schema})")

    def generate(
        self, raw_llm_output: Dict[str, Any], request_context: Optional[Dict[str, Any]] = None
    ) -> AgroLLMResponse:
        """Generate structured output from raw LLM output.

        Args:
            raw_llm_output: Raw output from LLM
            request_context: Original request context

        Returns:
            Structured AgroLLMResponse
        """
        # Extract components
        generated_text = raw_llm_output.get("text", "")
        diagnosis_data = raw_llm_output.get("diagnosis", {})
        rationales = raw_llm_output.get("rationales", [])

        # Build diagnosis card
        diagnosis_card = self._build_diagnosis_card(diagnosis_data)

        # Build explainability
        explainability = Explainability(
            rationales=rationales,
            reasoning_graph=raw_llm_output.get("reasoning_graph"),
            confidence_breakdown=raw_llm_output.get("confidence_breakdown"),
        )

        # Build flags
        flags = self._build_flags(diagnosis_card, raw_llm_output)

        # Create response
        response = AgroLLMResponse(
            generated_text=generated_text,
            diagnosis_card=diagnosis_card,
            explainability=explainability,
            flags=flags,
            metadata=raw_llm_output.get("metadata", {}),
        )

        # Validate if strict
        if self.strict_schema:
            self._validate_response(response)

        return response

    def _build_diagnosis_card(self, diagnosis_data: Dict[str, Any]) -> DiagnosisCard:
        """Build diagnosis card from raw data."""
        # Extract actions
        actions = []
        for action_data in diagnosis_data.get("actions", []):
            if isinstance(action_data, dict):
                actions.append(
                    RecommendedAction(
                        action=action_data.get("action", ""),
                        dose=action_data.get("dose"),
                        timing=action_data.get("timing"),
                        cost_est=action_data.get("cost_est"),
                        priority=action_data.get("priority", "medium"),
                    )
                )
            else:
                actions.append(RecommendedAction(action=str(action_data)))

        return DiagnosisCard(
            problem=diagnosis_data.get("problem", "No specific problem identified"),
            confidence=float(diagnosis_data.get("confidence", 0.5)),
            severity=diagnosis_data.get("severity", "medium"),
            evidence=diagnosis_data.get("evidence", []),
            recommended_actions=actions,
            warnings=diagnosis_data.get("warnings", []),
            citations=diagnosis_data.get("citations", []),
            metadata=diagnosis_data.get("metadata", {}),
        )

    def _build_flags(
        self, diagnosis_card: DiagnosisCard, raw_output: Dict[str, Any]
    ) -> ResponseFlags:
        """Build response flags."""
        return ResponseFlags(
            low_confidence=diagnosis_card.confidence < 0.6,
            needs_review=(
                diagnosis_card.severity == "high"
                or diagnosis_card.confidence < 0.5
                or raw_output.get("needs_review", False)
            ),
            safety_warning=len(diagnosis_card.warnings) > 0,
            constraint_violation=raw_output.get("constraint_violation", False),
        )

    def _validate_response(self, response: AgroLLMResponse) -> None:
        """Validate response against schema."""
        try:
            # Pydantic will validate on construction, but we can add additional checks
            if not response.generated_text:
                logger.warning("Response has empty generated_text")

            if response.diagnosis_card.confidence < 0.0 or response.diagnosis_card.confidence > 1.0:
                raise ValueError(f"Invalid confidence: {response.diagnosis_card.confidence}")

            if response.diagnosis_card.severity not in ["low", "medium", "high"]:
                raise ValueError(f"Invalid severity: {response.diagnosis_card.severity}")

        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            if self.strict_schema:
                raise
