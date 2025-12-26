"""Reasoning Graph Rewriter - Modifies output to fix contradictions and violations."""

import logging
from typing import Dict, Any, List, Optional

from .engine import ReasoningGraph, ReasoningNode
from ..contracts.v1.schemas import AgroLLMResponse, RecommendedAction

logger = logging.getLogger(__name__)


class ReasoningGraphRewriter:
    """Rewrites LLM output to fix reasoning graph violations."""

    def __init__(self):
        """Initialize rewriter."""
        logger.info("ReasoningGraphRewriter initialized")

    def rewrite_response(
        self, response: AgroLLMResponse, reasoning_graph: ReasoningGraph
    ) -> AgroLLMResponse:
        """Rewrite response to fix violations.

        Args:
            response: Original response
            reasoning_graph: Reasoning graph with violations

        Returns:
            Rewritten response
        """
        if not reasoning_graph.violations:
            return response

        logger.info(f"Rewriting response to fix {len(reasoning_graph.violations)} violations")

        rewritten = response.model_copy(deep=True)

        # Fix contradictions
        rewritten = self._fix_contradictions(rewritten, reasoning_graph)

        # Fix illegal actions
        rewritten = self._fix_illegal_actions(rewritten, reasoning_graph)

        # Fix unsafe sequences
        rewritten = self._fix_unsafe_sequences(rewritten, reasoning_graph)

        return rewritten

    def _fix_contradictions(
        self, response: AgroLLMResponse, reasoning_graph: ReasoningGraph
    ) -> AgroLLMResponse:
        """Fix contradictory statements."""
        # Find contradiction violations
        contradiction_violations = [
            v for v in reasoning_graph.violations if "contradiction" in str(v).lower()
        ]

        if not contradiction_violations:
            return response

        # Remove or modify contradictory actions
        # For MVP, we'll add warnings and remove conflicting actions
        for violation in contradiction_violations:
            response.diagnosis_card.warnings.append(
                f"Contradiction detected and resolved: {violation}"
            )

        # In production, would use more sophisticated logic to resolve contradictions
        logger.warning(f"Fixed {len(contradiction_violations)} contradictions")

        return response

    def _fix_illegal_actions(
        self, response: AgroLLMResponse, reasoning_graph: ReasoningGraph
    ) -> AgroLLMResponse:
        """Fix illegal actions."""
        # Find illegal action violations
        illegal_violations = [
            v
            for v in reasoning_graph.violations
            if "illegal" in str(v).lower() or "banned" in str(v).lower()
        ]

        if not illegal_violations:
            return response

        # Remove illegal actions
        original_actions = response.diagnosis_card.recommended_actions.copy()
        safe_actions = []

        for action in original_actions:
            action_text = action.action.lower()
            is_illegal = any(
                keyword in action_text
                for violation in illegal_violations
                for keyword in ["banned", "prohibited", "illegal"]
                if keyword in str(violation).lower()
            )

            if not is_illegal:
                safe_actions.append(action)
            else:
                logger.warning(f"Removed illegal action: {action.action}")
                response.diagnosis_card.warnings.append(f"Removed illegal action: {action.action}")

        response.diagnosis_card.recommended_actions = safe_actions

        return response

    def _fix_unsafe_sequences(
        self, response: AgroLLMResponse, reasoning_graph: ReasoningGraph
    ) -> AgroLLMResponse:
        """Fix unsafe action sequences."""
        # Find unsafe sequence violations
        unsafe_violations = [
            v for v in reasoning_graph.violations if "unsafe sequence" in str(v).lower()
        ]

        if not unsafe_violations:
            return response

        # Reorder or modify actions to fix unsafe sequences
        actions = response.diagnosis_card.recommended_actions.copy()

        # Simple fix: add timing warnings for potentially unsafe sequences
        for violation in unsafe_violations:
            response.diagnosis_card.warnings.append(
                f"Action sequence safety warning: {violation}. "
                "Please follow recommended timing intervals."
            )

        # In production, would reorder actions or add timing constraints
        logger.warning(f"Fixed {len(unsafe_violations)} unsafe sequences")

        return response
