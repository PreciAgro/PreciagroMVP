"""Explainability & Trace Engine - Produces evidence-linked reasoning traces."""

import logging
from typing import List, Dict, Any

from ..models.domain import (
    EvidenceGraph,
    Diagnosis,
    RecommendationPlan,
    ReasoningTrace,
)

logger = logging.getLogger(__name__)


class ExplainabilityTraceEngine:
    """Produces evidence-linked reasoning traces for trust, audits, and debugging."""
    
    def __init__(self):
        """Initialize the explainability trace engine."""
        pass
    
    def build_trace(
        self,
        evidence_graph: EvidenceGraph,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan,
        reasoning_steps: List[Dict[str, Any]]
    ) -> ReasoningTrace:
        """
        Build complete reasoning trace.
        
        Args:
            evidence_graph: Evidence graph
            diagnosis: Diagnosis result
            recommendation_plan: Recommendation plan
            reasoning_steps: Reasoning steps from reasoning core
            
        Returns:
            Complete reasoning trace
        """
        # Build rationale
        rationale = self._build_rationale(diagnosis, recommendation_plan)
        
        # Build confidence breakdown
        confidence_breakdown = self._build_confidence_breakdown(
            evidence_graph, diagnosis, recommendation_plan
        )
        
        # Extract applied rules
        applied_rules = self._extract_applied_rules(reasoning_steps)
        
        # Extract model inferences (if any)
        model_inferences = self._extract_model_inferences(reasoning_steps)
        
        trace = ReasoningTrace(
            evidence_graph_id=evidence_graph.id,
            diagnosis_id=diagnosis.id,
            steps=reasoning_steps,
            applied_rules=applied_rules,
            model_inferences=model_inferences,
            rationale=rationale,
            confidence_breakdown=confidence_breakdown,
        )
        
        logger.info(f"Built reasoning trace for diagnosis {diagnosis.id}")
        
        return trace
    
    def _build_rationale(
        self,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan
    ) -> str:
        """Build human-readable rationale."""
        rationale_parts = []
        
        # Diagnosis rationale
        if diagnosis.primary_hypothesis:
            rationale_parts.append(
                f"Primary diagnosis: {diagnosis.primary_hypothesis.name} "
                f"(confidence: {diagnosis.primary_hypothesis.belief_score:.2f})"
            )
            
            if diagnosis.hypotheses:
                rationale_parts.append(
                    f"Considered {len(diagnosis.hypotheses)} alternative hypotheses"
                )
        else:
            rationale_parts.append("No clear diagnosis identified")
        
        # Recommendation rationale
        if recommendation_plan.recommendations:
            rationale_parts.append(
                f"Generated {len(recommendation_plan.recommendations)} recommendations"
            )
            
            high_priority = [
                rec for rec in recommendation_plan.recommendations
                if rec.priority in ["high", "urgent"]
            ]
            if high_priority:
                rationale_parts.append(
                    f"{len(high_priority)} high-priority actions recommended"
                )
        else:
            rationale_parts.append("Monitoring recommended due to insufficient evidence")
        
        # Uncertainty rationale
        if diagnosis.uncertainty_reasons:
            rationale_parts.append(
                f"Uncertainty factors: {', '.join(diagnosis.uncertainty_reasons)}"
            )
        
        return ". ".join(rationale_parts) + "."
    
    def _build_confidence_breakdown(
        self,
        evidence_graph: EvidenceGraph,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan
    ) -> Dict[str, float]:
        """Build confidence breakdown by component."""
        breakdown = {}
        
        # Overall diagnosis confidence
        breakdown["diagnosis"] = diagnosis.overall_confidence
        
        # Primary hypothesis confidence
        if diagnosis.primary_hypothesis:
            breakdown["primary_hypothesis"] = diagnosis.primary_hypothesis.belief_score
        
        # Evidence confidence
        if evidence_graph.evidence:
            avg_evidence_confidence = sum(
                ev.confidence for ev in evidence_graph.evidence
            ) / len(evidence_graph.evidence)
            breakdown["evidence"] = avg_evidence_confidence
        
        # Observation confidence
        if evidence_graph.observations:
            avg_obs_confidence = sum(
                obs.confidence for obs in evidence_graph.observations
            ) / len(evidence_graph.observations)
            breakdown["observations"] = avg_obs_confidence
        
        # Recommendation confidence
        if recommendation_plan.recommendations:
            avg_rec_confidence = sum(
                rec.confidence for rec in recommendation_plan.recommendations
            ) / len(recommendation_plan.recommendations)
            breakdown["recommendations"] = avg_rec_confidence
        
        return breakdown
    
    def _extract_applied_rules(
        self,
        reasoning_steps: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract applied rules from reasoning steps."""
        rules = []
        
        for step in reasoning_steps:
            rule_type = step.get("rule_type")
            if rule_type:
                rules.append(f"{rule_type}: {step.get('description', '')}")
        
        return rules
    
    def _extract_model_inferences(
        self,
        reasoning_steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract ML model inferences from reasoning steps."""
        inferences = []
        
        for step in reasoning_steps:
            if step.get("model_type"):
                inferences.append({
                    "model_type": step.get("model_type"),
                    "input": step.get("input"),
                    "output": step.get("output"),
                    "confidence": step.get("confidence"),
                })
        
        return inferences

