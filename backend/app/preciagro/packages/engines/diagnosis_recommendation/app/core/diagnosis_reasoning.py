"""Diagnosis Reasoning Core - Applies reasoning to rank hypotheses."""

import logging
from typing import List, Dict, Any

from ..models.domain import (
    EvidenceGraph,
    Hypothesis,
    Diagnosis,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class DiagnosisReasoningCore:
    """Applies symbolic, probabilistic, temporal, and spatial reasoning to rank hypotheses."""

    def __init__(self):
        """Initialize the reasoning core."""
        self._reasoning_rules = self._build_reasoning_rules()

    def reason(
        self, hypotheses: List[Hypothesis], evidence_graph: EvidenceGraph, context: Dict[str, Any]
    ) -> Diagnosis:
        """
        Apply reasoning to rank hypotheses and create diagnosis.

        Args:
            hypotheses: List of generated hypotheses
            evidence_graph: Evidence graph
            context: Contextual information

        Returns:
            Ranked diagnosis
        """
        # Apply symbolic reasoning
        hypotheses = self._apply_symbolic_reasoning(hypotheses, evidence_graph, context)

        # Apply probabilistic reasoning
        hypotheses = self._apply_probabilistic_reasoning(hypotheses, evidence_graph, context)

        # Apply temporal reasoning
        hypotheses = self._apply_temporal_reasoning(hypotheses, evidence_graph, context)

        # Apply spatial reasoning
        hypotheses = self._apply_spatial_reasoning(hypotheses, evidence_graph, context)

        # Rank hypotheses by belief score
        hypotheses = sorted(hypotheses, key=lambda h: h.belief_score, reverse=True)

        # Filter low-confidence hypotheses
        hypotheses = [h for h in hypotheses if h.belief_score >= settings.MIN_CONFIDENCE_THRESHOLD]

        # Select primary hypothesis
        primary_hypothesis = hypotheses[0] if hypotheses else None

        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(hypotheses, evidence_graph)

        # Identify uncertainty reasons
        uncertainty_reasons = self._identify_uncertainty_reasons(
            hypotheses, evidence_graph, context
        )

        # Create diagnosis
        diagnosis = Diagnosis(
            hypotheses=hypotheses,
            primary_hypothesis=primary_hypothesis,
            overall_confidence=overall_confidence,
            uncertainty_reasons=uncertainty_reasons,
        )

        logger.info(
            f"Reasoned diagnosis with {len(hypotheses)} hypotheses, "
            f"primary: {primary_hypothesis.name if primary_hypothesis else 'none'}, "
            f"confidence: {overall_confidence:.2f}"
        )

        return diagnosis

    def _apply_symbolic_reasoning(
        self, hypotheses: List[Hypothesis], evidence_graph: EvidenceGraph, context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Apply symbolic reasoning rules."""
        updated_hypotheses = []

        for hypothesis in hypotheses:
            # Apply category-specific rules
            if hypothesis.category.value == "disease":
                # Diseases are more likely in certain seasons
                season = context.get("current_season")
                if season in ["rainy", "wet"]:
                    hypothesis.belief_score *= 1.2  # Boost for disease in wet season

            elif hypothesis.category.value == "pest":
                # Pests are more likely in certain growth stages
                growth_stage = context.get("growth_stage")
                if growth_stage in ["vegetative", "flowering"]:
                    hypothesis.belief_score *= 1.15

            elif hypothesis.category.value == "nutrient_deficiency":
                # Nutrient deficiencies show specific patterns
                soil_obs = [
                    obs for obs in evidence_graph.observations if obs.signal.startswith("soil_")
                ]
                if soil_obs:
                    hypothesis.belief_score *= 1.1

            # Apply evidence strength rules
            supporting_evidence = [
                ev for ev in evidence_graph.evidence if ev.id in hypothesis.evidence_ids
            ]

            if supporting_evidence:
                avg_evidence_strength = sum(ev.strength for ev in supporting_evidence) / len(
                    supporting_evidence
                )
                hypothesis.belief_score = min(
                    1.0, hypothesis.belief_score * (0.5 + avg_evidence_strength)
                )

            updated_hypotheses.append(hypothesis)

        return updated_hypotheses

    def _apply_probabilistic_reasoning(
        self, hypotheses: List[Hypothesis], evidence_graph: EvidenceGraph, context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Apply probabilistic reasoning (Bayesian updating)."""
        updated_hypotheses = []

        for hypothesis in hypotheses:
            # Get supporting evidence
            supporting_evidence = [
                ev for ev in evidence_graph.evidence if ev.id in hypothesis.evidence_ids
            ]

            if supporting_evidence:
                # Simple Bayesian update: P(H|E) = P(E|H) * P(H) / P(E)
                # Simplified: belief = prior * evidence_likelihood
                evidence_likelihood = sum(
                    ev.strength * ev.confidence for ev in supporting_evidence
                ) / len(supporting_evidence)

                # Update belief score
                hypothesis.belief_score = min(
                    1.0, hypothesis.prior_probability * (1.0 + evidence_likelihood)
                )

            updated_hypotheses.append(hypothesis)

        return updated_hypotheses

    def _apply_temporal_reasoning(
        self, hypotheses: List[Hypothesis], evidence_graph: EvidenceGraph, context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Apply temporal reasoning."""
        updated_hypotheses = []

        # Check temporal validity of hypotheses
        current_season = context.get("current_season")
        growth_stage = context.get("growth_stage")

        for hypothesis in hypotheses:
            # Check if hypothesis is temporally valid
            if hypothesis.temporal_validity:
                valid_seasons = hypothesis.temporal_validity.get("seasons", [])
                valid_stages = hypothesis.temporal_validity.get("growth_stages", [])

                if valid_seasons and current_season not in valid_seasons:
                    hypothesis.belief_score *= 0.7  # Reduce if temporally invalid

                if valid_stages and growth_stage not in valid_stages:
                    hypothesis.belief_score *= 0.8  # Reduce if stage invalid

            # Check for temporal patterns in evidence
            temporal_evidence = [
                ev
                for ev in evidence_graph.evidence
                if ev.id in hypothesis.evidence_ids and ev.type.value == "temporal"
            ]

            if temporal_evidence:
                hypothesis.belief_score *= 1.1  # Boost for temporal patterns

            updated_hypotheses.append(hypothesis)

        return updated_hypotheses

    def _apply_spatial_reasoning(
        self, hypotheses: List[Hypothesis], evidence_graph: EvidenceGraph, context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Apply spatial reasoning."""
        updated_hypotheses = []

        # Check spatial validity
        region_code = context.get("region_code")

        for hypothesis in hypotheses:
            # Check if hypothesis is spatially valid
            if hypothesis.spatial_validity:
                valid_regions = hypothesis.spatial_validity.get("regions", [])

                if valid_regions and region_code not in valid_regions:
                    hypothesis.belief_score *= 0.6  # Reduce if spatially invalid

            # Check for spatial patterns in evidence
            spatial_evidence = [
                ev
                for ev in evidence_graph.evidence
                if ev.id in hypothesis.evidence_ids and ev.type.value == "spatial"
            ]

            if spatial_evidence:
                hypothesis.belief_score *= 1.05  # Slight boost for spatial patterns

            updated_hypotheses.append(hypothesis)

        return updated_hypotheses

    def _calculate_overall_confidence(
        self, hypotheses: List[Hypothesis], evidence_graph: EvidenceGraph
    ) -> float:
        """Calculate overall confidence in diagnosis."""
        if not hypotheses:
            return 0.0

        # Weighted average of top hypotheses
        top_hypotheses = hypotheses[:3]  # Top 3
        weights = [0.5, 0.3, 0.2]  # Decreasing weights

        overall = sum(h.belief_score * w for h, w in zip(top_hypotheses, weights))

        # Adjust based on evidence quality
        all_evidence = evidence_graph.evidence
        if all_evidence:
            avg_evidence_confidence = sum(ev.confidence for ev in all_evidence) / len(all_evidence)
            overall = (overall + avg_evidence_confidence) / 2

        return min(1.0, overall)

    def _identify_uncertainty_reasons(
        self, hypotheses: List[Hypothesis], evidence_graph: EvidenceGraph, context: Dict[str, Any]
    ) -> List[str]:
        """Identify reasons for uncertainty."""
        reasons = []

        # Check hypothesis confidence
        if hypotheses:
            top_confidence = hypotheses[0].belief_score
            if top_confidence < 0.6:
                reasons.append(f"Low confidence in primary hypothesis ({top_confidence:.2f})")

        # Check number of observations
        if len(evidence_graph.observations) < 3:
            reasons.append("Limited observations available")

        # Check evidence quality
        if evidence_graph.evidence:
            low_confidence_evidence = [ev for ev in evidence_graph.evidence if ev.confidence < 0.5]
            if len(low_confidence_evidence) > len(evidence_graph.evidence) / 2:
                reasons.append("Many low-confidence evidence sources")

        # Check for conflicting hypotheses
        if len(hypotheses) > 1:
            top_two_diff = abs(hypotheses[0].belief_score - hypotheses[1].belief_score)
            if top_two_diff < 0.1:
                reasons.append("Multiple hypotheses with similar confidence")

        # Check missing context
        missing_context = []
        if not context.get("crop_type"):
            missing_context.append("crop_type")
        if not context.get("region_code"):
            missing_context.append("region_code")
        if missing_context:
            reasons.append(f"Missing context: {', '.join(missing_context)}")

        return reasons

    def _build_reasoning_rules(self) -> Dict[str, Any]:
        """Build reasoning rules."""
        return {
            "symbolic_boost": 1.2,
            "temporal_penalty": 0.7,
            "spatial_penalty": 0.6,
            "evidence_strength_weight": 0.5,
        }
