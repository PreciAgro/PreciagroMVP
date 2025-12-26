"""Main Diagnosis & Recommendation Engine service."""

import logging
import time
from typing import Dict, Any

from ..contracts.v1.schemas import DREInput, DREResponse
from ..core.input_harmonization import InputHarmonizationLayer
from ..core.evidence_graph import EvidenceGraphBuilder
from ..core.hypothesis_generation import HypothesisGenerationLayer
from ..core.diagnosis_reasoning import DiagnosisReasoningCore
from ..core.recommendation_synthesis import RecommendationSynthesisCore
from ..core.constraint_safety import ConstraintSafetyEngine
from ..core.confidence_uncertainty import ConfidenceUncertaintyEngine
from ..core.explainability_trace import ExplainabilityTraceEngine
from ..core.output_packaging import OutputPackagingLayer
from ..core.config import settings

logger = logging.getLogger(__name__)


class DiagnosisRecommendationEngine:
    """Main engine orchestrating all components."""

    def __init__(self):
        """Initialize the engine with all components."""
        self.input_harmonization = InputHarmonizationLayer()
        self.evidence_graph_builder = EvidenceGraphBuilder()
        self.hypothesis_generation = HypothesisGenerationLayer()
        self.diagnosis_reasoning = DiagnosisReasoningCore()
        self.recommendation_synthesis = RecommendationSynthesisCore()
        self.constraint_safety = ConstraintSafetyEngine()
        self.confidence_uncertainty = ConfidenceUncertaintyEngine()
        self.explainability_trace = ExplainabilityTraceEngine()
        self.output_packaging = OutputPackagingLayer()

    async def process(self, input_data: DREInput) -> DREResponse:
        """
        Process input and generate diagnosis with recommendations.

        Args:
            input_data: Input from upstream engines

        Returns:
            Complete diagnosis and recommendation response
        """
        processing_start_time = time.time()

        try:
            # Step 1: Harmonize inputs
            logger.info(f"Processing request {input_data.request_id}")
            observations = self.input_harmonization.harmonize(input_data)

            if not observations:
                logger.warning("No observations generated from input")
                # Return minimal response
                return self._create_minimal_response(input_data, processing_start_time)

            # Step 2: Build evidence graph
            context = self._extract_context(input_data)
            evidence_graph = self.evidence_graph_builder.build_graph(observations, context)

            # Step 3: Generate hypotheses
            hypotheses = self.hypothesis_generation.generate_hypotheses(evidence_graph, context)

            # Step 4: Reason about hypotheses
            reasoning_steps = []  # Track reasoning steps for trace
            diagnosis = self.diagnosis_reasoning.reason(hypotheses, evidence_graph, context)

            # Step 5: Synthesize recommendations
            recommendation_plan = self.recommendation_synthesis.synthesize(diagnosis, context)

            # Step 6: Validate constraints and safety
            validated_plan, constraint_violations = self.constraint_safety.validate_plan(
                recommendation_plan, context
            )

            # Step 7: Quantify confidence and uncertainty
            uncertainty_metric = self.confidence_uncertainty.quantify(
                diagnosis, validated_plan, evidence_graph, context
            )

            # Step 8: Build reasoning trace
            reasoning_trace = self.explainability_trace.build_trace(
                evidence_graph, diagnosis, validated_plan, reasoning_steps
            )

            # Step 9: Package output
            response = self.output_packaging.package(
                input_data.request_id,
                diagnosis,
                validated_plan,
                reasoning_trace,
                uncertainty_metric,
                constraint_violations,
                processing_start_time,
                context,
            )

            logger.info(
                f"Successfully processed request {input_data.request_id}: "
                f"{len(diagnosis.hypotheses)} hypotheses, "
                f"{len(validated_plan.recommendations)} recommendations"
            )

            return response

        except Exception as e:
            logger.error(f"Error processing request {input_data.request_id}: {e}", exc_info=True)
            # Return error response with minimal information
            return self._create_error_response(input_data, str(e), processing_start_time)

    def _extract_context(self, input_data: DREInput) -> Dict[str, Any]:
        """Extract context from input data."""
        context = {
            "request_id": input_data.request_id,
            "farmer_id": input_data.farmer_id,
            "field_id": input_data.field_id,
            "language": input_data.language,
            "urgency": input_data.urgency,
        }

        # Extract from geo context
        if input_data.geo_context:
            context["region_code"] = input_data.geo_context.region_code
            context["soil_data"] = input_data.geo_context.soil_data
            context["climate_data"] = input_data.geo_context.climate_data
            context["spatial_context"] = input_data.geo_context.spatial_context

        # Extract from temporal logic
        if input_data.temporal_logic:
            context["current_season"] = input_data.temporal_logic.current_season
            context["growth_stage"] = input_data.temporal_logic.growth_stage
            context["timing_windows"] = input_data.temporal_logic.timing_windows

        # Extract from crop intelligence
        if input_data.crop_intelligence:
            context["crop_type"] = input_data.crop_intelligence.crop_type
            context["variety"] = input_data.crop_intelligence.variety
            context["health_status"] = input_data.crop_intelligence.health_status

        # Extract from inventory
        if input_data.inventory:
            context["inventory"] = {
                "available_inputs": input_data.inventory.available_inputs,
                "stock_levels": input_data.inventory.stock_levels,
            }

        # Extract from farmer profile
        if input_data.farmer_profile:
            context["farmer_profile"] = {
                "preferences": input_data.farmer_profile.preferences,
                "constraints": input_data.farmer_profile.constraints,
                "budget_class": input_data.farmer_profile.budget_class,
            }

        # Extract signals for context
        context["image_analysis"] = input_data.image_analysis is not None
        context["sensors"] = input_data.sensors is not None

        return context

    def _create_minimal_response(
        self, input_data: DREInput, processing_start_time: float
    ) -> DREResponse:
        """Create minimal response when no observations are available."""
        from ..models.domain import (
            Diagnosis,
            Hypothesis,
            HypothesisCategory,
            RecommendationPlan,
            Recommendation,
            ActionType,
            ReasoningTrace,
            UncertaintyMetric,
            EvidenceGraph,
        )

        # Create minimal diagnosis
        unknown_hypothesis = Hypothesis(
            category=HypothesisCategory.UNKNOWN,
            name="Unknown Cause",
            description="Insufficient data to generate diagnosis",
            belief_score=0.1,
        )

        diagnosis = Diagnosis(
            hypotheses=[unknown_hypothesis],
            primary_hypothesis=unknown_hypothesis,
            overall_confidence=0.1,
            uncertainty_reasons=["No observations available from upstream engines"],
        )

        # Create monitoring recommendation
        monitoring_rec = Recommendation(
            type=ActionType.MONITORING,
            title="Collect Additional Data",
            description="Please provide additional observations (images, symptoms, sensor data) to enable diagnosis",
            steps=[
                "Take photos of affected areas",
                "Describe symptoms in detail",
                "Provide sensor readings if available",
            ],
            priority="low",
            impact_score=0.2,
            confidence=0.1,
        )

        recommendation_plan = RecommendationPlan(
            recommendations=[monitoring_rec],
            execution_order=[monitoring_rec.id],
        )

        # Create minimal trace
        evidence_graph = EvidenceGraph(observations=[], evidence=[])
        reasoning_trace = ReasoningTrace(
            evidence_graph_id=evidence_graph.id,
            diagnosis_id=diagnosis.id,
            steps=[],
            rationale="Insufficient data to perform diagnosis",
        )

        # Create uncertainty metric
        uncertainty_metric = UncertaintyMetric(
            overall_uncertainty=0.9,
            missing_data=["image_analysis", "sensors", "conversational_nlp"],
            escalation_required=True,
            escalation_reasons=["No observations available"],
        )

        # Package response
        response = self.output_packaging.package(
            input_data.request_id,
            diagnosis,
            recommendation_plan,
            reasoning_trace,
            uncertainty_metric,
            [],
            processing_start_time,
            self._extract_context(input_data),
        )

        return response

    def _create_error_response(
        self, input_data: DREInput, error_message: str, processing_start_time: float
    ) -> DREResponse:
        """Create error response."""
        # Similar to minimal response but with error indication
        response = self._create_minimal_response(input_data, processing_start_time)
        response.escalation_reasons.append(f"Processing error: {error_message}")
        response.needs_human_review = True
        return response
