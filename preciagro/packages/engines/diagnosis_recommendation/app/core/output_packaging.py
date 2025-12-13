"""Output Packaging Layer - Emits clean, engine-consumable outputs."""

import logging
from typing import Dict, Any
import time

from ..models.domain import (
    Diagnosis,
    RecommendationPlan,
    ReasoningTrace,
    UncertaintyMetric,
)
from ..contracts.v1.schemas import (
    DREResponse,
    DiagnosisResult,
    RecommendationResult,
    SafetyWarning,
    DataRequest,
)

logger = logging.getLogger(__name__)


class OutputPackagingLayer:
    """Emits clean, engine-consumable outputs without UI assumptions."""
    
    def __init__(self):
        """Initialize the output packaging layer."""
        pass
    
    def package(
        self,
        request_id: str,
        diagnosis: Diagnosis,
        recommendation_plan: RecommendationPlan,
        reasoning_trace: ReasoningTrace,
        uncertainty_metric: UncertaintyMetric,
        constraint_violations: list,
        processing_start_time: float,
        context: Dict[str, Any]
    ) -> DREResponse:
        """
        Package all outputs into engine-consumable response.
        
        Args:
            request_id: Original request ID
            diagnosis: Diagnosis result
            recommendation_plan: Recommendation plan
            reasoning_trace: Reasoning trace
            uncertainty_metric: Uncertainty metrics
            constraint_violations: Constraint violations
            processing_start_time: Processing start time
            context: Contextual information
            
        Returns:
            Packaged response
        """
        # Calculate processing time
        processing_time_ms = (time.time() - processing_start_time) * 1000
        
        # Package diagnosis
        diagnosis_result = self._package_diagnosis(diagnosis)
        
        # Package recommendations
        recommendation_result = self._package_recommendations(recommendation_plan)
        
        # Package warnings
        warnings = self._package_warnings(recommendation_plan, constraint_violations)
        
        # Package data requests
        data_requests = self._package_data_requests(uncertainty_metric, context)
        
        # Package constraint violations
        constraint_violations_dict = [
            {
                "constraint_type": v.constraint_type,
                "severity": v.severity,
                "message": v.message,
                "recommendation_id": v.recommendation_id,
                "details": v.details,
            }
            for v in constraint_violations
        ]
        
        # Package evidence summary
        evidence_summary = self._package_evidence_summary(reasoning_trace)
        
        # Determine if human review is needed
        needs_human_review = uncertainty_metric.escalation_required
        
        response = DREResponse(
            request_id=request_id,
            diagnosis=diagnosis_result,
            recommendations=recommendation_result,
            overall_confidence=diagnosis.overall_confidence,
            uncertainty_metrics={
                "overall_uncertainty": uncertainty_metric.overall_uncertainty,
                "component_uncertainties": uncertainty_metric.component_uncertainties,
                "missing_data": uncertainty_metric.missing_data,
                "low_confidence_sources": uncertainty_metric.low_confidence_sources,
            },
            missing_data=uncertainty_metric.missing_data,
            warnings=warnings,
            constraint_violations=constraint_violations_dict,
            reasoning_trace_id=reasoning_trace.id,
            evidence_summary=evidence_summary,
            data_requests=data_requests,
            needs_human_review=needs_human_review,
            escalation_reasons=uncertainty_metric.escalation_reasons,
            processing_time_ms=processing_time_ms,
            metadata={
                "diagnosis_id": diagnosis.id,
                "plan_id": recommendation_plan.id,
            },
        )
        
        logger.info(
            f"Packaged response: diagnosis_id={diagnosis.id}, "
            f"recommendations={len(recommendation_plan.recommendations)}, "
            f"processing_time={processing_time_ms:.1f}ms"
        )
        
        return response
    
    def _package_diagnosis(self, diagnosis: Diagnosis) -> DiagnosisResult:
        """Package diagnosis into response format."""
        all_hypotheses = [
            {
                "id": h.id,
                "category": h.category.value,
                "name": h.name,
                "description": h.description,
                "belief_score": h.belief_score,
                "severity": h.severity,
                "urgency": h.urgency,
            }
            for h in diagnosis.hypotheses
        ]
        
        return DiagnosisResult(
            diagnosis_id=diagnosis.id,
            primary_hypothesis=diagnosis.primary_hypothesis.name if diagnosis.primary_hypothesis else "Unknown",
            primary_confidence=diagnosis.primary_hypothesis.belief_score if diagnosis.primary_hypothesis else 0.0,
            all_hypotheses=all_hypotheses,
            overall_confidence=diagnosis.overall_confidence,
            uncertainty_reasons=diagnosis.uncertainty_reasons,
        )
    
    def _package_recommendations(
        self,
        recommendation_plan: RecommendationPlan
    ) -> RecommendationResult:
        """Package recommendations into response format."""
        recommendations_dict = [
            {
                "id": rec.id,
                "type": rec.type.value,
                "title": rec.title,
                "description": rec.description,
                "steps": rec.steps,
                "timing": rec.timing,
                "frequency": rec.frequency,
                "dosage": rec.dosage,
                "priority": rec.priority,
                "impact_score": rec.impact_score,
                "cost_estimate": rec.cost_estimate,
                "warnings": rec.warnings,
                "prerequisites": rec.prerequisites,
                "confidence": rec.confidence,
                "alternatives": rec.alternatives,
            }
            for rec in recommendation_plan.recommendations
        ]
        
        return RecommendationResult(
            plan_id=recommendation_plan.id,
            recommendations=recommendations_dict,
            execution_order=recommendation_plan.execution_order,
            total_estimated_cost=recommendation_plan.total_estimated_cost,
            is_validated=recommendation_plan.is_validated,
        )
    
    def _package_warnings(
        self,
        recommendation_plan: RecommendationPlan,
        constraint_violations: list
    ) -> list[SafetyWarning]:
        """Package warnings into response format."""
        warnings = []
        
        # Add warnings from recommendations
        for rec in recommendation_plan.recommendations:
            for warning_msg in rec.warnings:
                warnings.append(SafetyWarning(
                    level="warning",
                    message=warning_msg,
                    recommendation_id=rec.id,
                ))
        
        # Add warnings from constraint violations
        for violation in constraint_violations:
            if violation.severity in ["warning", "error"]:
                level = "error" if violation.severity == "error" else "warning"
                warnings.append(SafetyWarning(
                    level=level,
                    message=violation.message,
                    recommendation_id=violation.recommendation_id,
                    constraint_type=violation.constraint_type,
                ))
        
        return warnings
    
    def _package_data_requests(
        self,
        uncertainty_metric: UncertaintyMetric,
        context: Dict[str, Any]
    ) -> list[DataRequest]:
        """Package data requests into response format."""
        requests = []
        
        # Request missing data sources
        for missing_source in uncertainty_metric.missing_data:
            source_engine_map = {
                "image_analysis": "Image Analysis Engine",
                "sensors": "Sensor Engine",
                "soil_data": "GeoContext Engine",
                "weather_data": "Data Integration Engine",
                "crop_intelligence": "Crop Intelligence Engine",
            }
            
            engine_name = source_engine_map.get(missing_source, "Unknown Engine")
            
            requests.append(DataRequest(
                data_type=missing_source,
                source_engine=engine_name,
                reason=f"Missing {missing_source} data would improve diagnosis confidence",
                priority="medium" if missing_source in ["image_analysis", "crop_intelligence"] else "low",
            ))
        
        return requests
    
    def _package_evidence_summary(
        self,
        reasoning_trace: ReasoningTrace
    ) -> Dict[str, Any]:
        """Package evidence summary into response format."""
        return {
            "evidence_count": len(reasoning_trace.steps),
            "applied_rules": reasoning_trace.applied_rules,
            "model_inferences_count": len(reasoning_trace.model_inferences),
            "rationale": reasoning_trace.rationale,
        }

