"""Confidence & Uncertainty Engine - Quantifies certainty and surfaces unknowns."""

import logging
from typing import List, Dict, Any

from ..models.domain import (
    Diagnosis,
    RecommendationPlan,
    UncertaintyMetric,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class ConfidenceUncertaintyEngine:
    """Quantifies certainty, surfaces unknowns, and triggers escalation paths."""

    def __init__(self):
        """Initialize the confidence and uncertainty engine."""
        pass

    def quantify(
        self,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan,
        evidence_graph,
        context: Dict[str, Any],
    ) -> UncertaintyMetric:
        """
        Quantify confidence and uncertainty.

        Args:
            diagnosis: Diagnosis result
            recommendation_plan: Recommendation plan
            evidence_graph: Evidence graph
            context: Contextual information

        Returns:
            Uncertainty metrics
        """
        # Calculate overall uncertainty
        overall_uncertainty = self._calculate_overall_uncertainty(
            diagnosis, recommendation_plan, evidence_graph
        )

        # Calculate component uncertainties
        component_uncertainties = self._calculate_component_uncertainties(
            diagnosis, recommendation_plan, evidence_graph, context
        )

        # Identify missing data
        missing_data = self._identify_missing_data(context)

        # Identify low confidence sources
        low_confidence_sources = self._identify_low_confidence_sources(evidence_graph)

        # Determine if escalation is required
        escalation_required = self._should_escalate(
            overall_uncertainty, diagnosis, recommendation_plan
        )

        escalation_reasons = []
        if escalation_required:
            escalation_reasons = self._get_escalation_reasons(
                overall_uncertainty, diagnosis, recommendation_plan, missing_data
            )

        metric = UncertaintyMetric(
            overall_uncertainty=overall_uncertainty,
            component_uncertainties=component_uncertainties,
            missing_data=missing_data,
            low_confidence_sources=low_confidence_sources,
            escalation_required=escalation_required,
            escalation_reasons=escalation_reasons,
        )

        logger.info(
            f"Quantified uncertainty: overall={overall_uncertainty:.2f}, "
            f"escalation={escalation_required}"
        )

        return metric

    def _calculate_overall_uncertainty(
        self, diagnosis: Diagnosis, recommendation_plan: RecommendationPlan, evidence_graph
    ) -> float:
        """Calculate overall uncertainty score (0=certain, 1=uncertain)."""
        # Start with diagnosis confidence (inverted)
        uncertainty = 1.0 - diagnosis.overall_confidence

        # Adjust based on number of hypotheses
        if len(diagnosis.hypotheses) > 1:
            # Multiple hypotheses increase uncertainty
            top_two_diff = abs(
                diagnosis.hypotheses[0].belief_score - diagnosis.hypotheses[1].belief_score
            )
            if top_two_diff < 0.15:  # Close scores
                uncertainty += 0.2

        # Adjust based on evidence quality
        if evidence_graph.evidence:
            avg_evidence_confidence = sum(ev.confidence for ev in evidence_graph.evidence) / len(
                evidence_graph.evidence
            )
            uncertainty += (1.0 - avg_evidence_confidence) * 0.3

        # Adjust based on number of observations
        if len(evidence_graph.observations) < 3:
            uncertainty += 0.2

        return min(1.0, uncertainty)

    def _calculate_component_uncertainties(
        self,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan,
        evidence_graph,
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate uncertainty per component."""
        uncertainties = {}

        # Diagnosis uncertainty
        uncertainties["diagnosis"] = 1.0 - diagnosis.overall_confidence

        # Hypothesis uncertainty
        if diagnosis.hypotheses:
            primary_confidence = diagnosis.hypotheses[0].belief_score
            uncertainties["primary_hypothesis"] = 1.0 - primary_confidence
        else:
            uncertainties["primary_hypothesis"] = 1.0

        # Evidence uncertainty
        if evidence_graph.evidence:
            avg_evidence_confidence = sum(ev.confidence for ev in evidence_graph.evidence) / len(
                evidence_graph.evidence
            )
            uncertainties["evidence"] = 1.0 - avg_evidence_confidence
        else:
            uncertainties["evidence"] = 1.0

        # Observation uncertainty
        if evidence_graph.observations:
            avg_obs_confidence = sum(obs.confidence for obs in evidence_graph.observations) / len(
                evidence_graph.observations
            )
            uncertainties["observations"] = 1.0 - avg_obs_confidence
        else:
            uncertainties["observations"] = 1.0

        # Recommendation uncertainty
        if recommendation_plan.recommendations:
            avg_rec_confidence = sum(
                rec.confidence for rec in recommendation_plan.recommendations
            ) / len(recommendation_plan.recommendations)
            uncertainties["recommendations"] = 1.0 - avg_rec_confidence
        else:
            uncertainties["recommendations"] = 1.0

        # Context uncertainty
        context_completeness = self._calculate_context_completeness(context)
        uncertainties["context"] = 1.0 - context_completeness

        return uncertainties

    def _calculate_context_completeness(self, context: Dict[str, Any]) -> float:
        """Calculate how complete the context is."""
        required_fields = [
            "crop_type",
            "region_code",
            "current_season",
            "growth_stage",
        ]

        present_fields = sum(1 for field in required_fields if context.get(field))
        completeness = present_fields / len(required_fields)

        return completeness

    def _identify_missing_data(self, context: Dict[str, Any]) -> List[str]:
        """Identify missing data sources."""
        missing = []

        # Check for key data sources
        if not context.get("image_analysis"):
            missing.append("image_analysis")

        if not context.get("sensors"):
            missing.append("sensors")

        if not context.get("soil_data"):
            missing.append("soil_data")

        if not context.get("weather_data"):
            missing.append("weather_data")

        if not context.get("crop_intelligence"):
            missing.append("crop_intelligence")

        return missing

    def _identify_low_confidence_sources(self, evidence_graph) -> List[str]:
        """Identify low confidence observation sources."""
        low_confidence_sources = []

        # Group observations by source
        source_confidence: Dict[str, List[float]] = {}
        for obs in evidence_graph.observations:
            source = obs.source.value
            if source not in source_confidence:
                source_confidence[source] = []
            source_confidence[source].append(obs.confidence)

        # Identify sources with low average confidence
        for source, confidences in source_confidence.items():
            avg_confidence = sum(confidences) / len(confidences)
            if avg_confidence < 0.5:
                low_confidence_sources.append(source)

        return low_confidence_sources

    def _should_escalate(
        self,
        overall_uncertainty: float,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan,
    ) -> bool:
        """Determine if human review is required."""
        # Escalate if uncertainty is high
        if overall_uncertainty > (1.0 - settings.ESCALATION_CONFIDENCE_THRESHOLD):
            return True

        # Escalate if diagnosis confidence is very low
        if diagnosis.overall_confidence < settings.ESCALATION_CONFIDENCE_THRESHOLD:
            return True

        # Escalate if blocking actions with low confidence
        if settings.BLOCK_LOW_CONFIDENCE_ACTIONS:
            high_priority_recs = [
                rec
                for rec in recommendation_plan.recommendations
                if rec.priority in ["high", "urgent"]
            ]

            for rec in high_priority_recs:
                if rec.confidence < settings.ESCALATION_CONFIDENCE_THRESHOLD:
                    return True

        return False

    def _get_escalation_reasons(
        self,
        overall_uncertainty: float,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan,
        missing_data: List[str],
    ) -> List[str]:
        """Get reasons for escalation."""
        reasons = []

        if overall_uncertainty > 0.6:
            reasons.append(f"High overall uncertainty ({overall_uncertainty:.2f})")

        if diagnosis.overall_confidence < settings.ESCALATION_CONFIDENCE_THRESHOLD:
            reasons.append(f"Low diagnosis confidence ({diagnosis.overall_confidence:.2f})")

        if missing_data:
            reasons.append(f"Missing critical data sources: {', '.join(missing_data)}")

        if not diagnosis.primary_hypothesis:
            reasons.append("No primary hypothesis identified")

        # Check for high-risk recommendations with low confidence
        high_risk_recs = [
            rec
            for rec in recommendation_plan.recommendations
            if rec.priority in ["high", "urgent"] and rec.confidence < 0.6
        ]

        if high_risk_recs:
            reasons.append(
                f"{len(high_risk_recs)} high-priority recommendations with low confidence"
            )

        return reasons
