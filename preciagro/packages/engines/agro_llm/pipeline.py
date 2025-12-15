"""Main AgroLLM Pipeline - Wires all modules together."""

import logging
from typing import Dict, Any, Optional

from .contracts.v1.schemas import FarmerRequest, AgroLLMResponse
from .normalization import InputNormalizer
from .fusion import MultiModalFusionEngine
from .rag import RAGAdapter
from .knowledge_graph import KnowledgeGraphAdapter
from .local import LocalIntelligenceAdapter
from .core import AgroLLMWrapper, LLMMode
from .core.confidence import ConfidenceCalibrator, ConfidenceFactors
from .safety import SafetyConstraintEngine
from .safety.temporal_safety import TemporalSafetyValidator
from .reasoning_graph import ReasoningGraphEngine
from .reasoning_graph.rewriter import ReasoningGraphRewriter
from .output import StructuredOutputGenerator
from .output.safety_postprocessor import SafetyPostProcessor, SafetyPostProcessorConfig
from .feedback import FeedbackHooks
from .feedback.event_emitter import EventEmitter
from .fallback import FallbackEngine, FallbackMode
from .clients import (
    ImageAnalysisClient,
    GeoContextClient,
    TemporalLogicClient,
    CropIntelligenceClient,
    DataIntegrationClient,
    InventoryClient,
    SecurityAccessClient,
    OrchestratorClient,
    StubImageAnalysisClient,
)
from .config import ConfigLoader, AgroLLMConfig

logger = logging.getLogger(__name__)


class AgroLLMPipeline:
    """Main pipeline orchestrating all AgroLLM components."""

    def __init__(self, config: Optional[AgroLLMConfig] = None):
        """Initialize pipeline with configuration.

        Args:
            config: Configuration object (if None, loads from default)
        """
        # Load configuration
        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.load()
        self.config = config

        # Initialize components
        self.normalizer = InputNormalizer()
        self.fusion_engine = MultiModalFusionEngine()

        # Initialize adapters
        self.rag_adapter = RAGAdapter(vector_db_endpoint=config.rag_endpoint, top_k=5)
        self.kg_adapter = KnowledgeGraphAdapter(kg_endpoint=config.kg_endpoint, kg_api_key=None)
        self.local_adapter = LocalIntelligenceAdapter(
            local_rules_dir=config.region_rules.rules_directory
        )

        # Initialize LLM wrapper
        llm_mode = LLMMode(config.model_provider.mode)
        self.llm_wrapper = AgroLLMWrapper(
            mode=llm_mode,
            model_name=config.model_provider.model_name,
            api_endpoint=config.model_provider.api_endpoint,
            api_key=config.model_provider.api_key,
        )

        # Initialize safety and reasoning
        self.safety_engine = SafetyConstraintEngine(
            config={
                "banned_chemicals": config.safety_rules.banned_chemicals,
                "strict_mode": config.safety_rules.strict_mode,
                "region_compliance": config.region_compliance,
            }
        )
        self.temporal_safety_validator = (
            TemporalSafetyValidator(
                config={
                    "phi_rules": config.temporal_safety.phi_rules,
                    "crop_stage_rules": config.temporal_safety.crop_stage_rules,
                    "season_rules": config.region_compliance.get("region_constraints", {}),
                }
            )
            if config.temporal_safety.enabled
            else None
        )

        self.reasoning_engine = ReasoningGraphEngine(strict_mode=config.safety_rules.strict_mode)
        self.reasoning_rewriter = ReasoningGraphRewriter()

        # Initialize output processing
        self.output_generator = StructuredOutputGenerator(strict_schema=True)
        self.safety_postprocessor = SafetyPostProcessor(
            config=SafetyPostProcessorConfig(
                banned_chemicals=config.safety_rules.banned_chemicals,
                illegal_dose_patterns=[],
                unsafe_timing_keywords=[],
                required_warnings_for_high_severity=config.safety_rules.require_warnings_for_high_severity,
                validate_region_codes=True,
                valid_region_codes=config.region_compliance.get("valid_regions", []),
            )
        )

        # Initialize confidence calibrator
        self.confidence_calibrator = ConfidenceCalibrator()

        # Initialize fallback engine
        fallback_mode = (
            FallbackMode(config.fallback.mode) if config.fallback.enabled else FallbackMode.NONE
        )
        self.fallback_engine = (
            FallbackEngine(mode=fallback_mode) if config.fallback.enabled else None
        )

        # Initialize client interfaces
        self.image_client = StubImageAnalysisClient(endpoint=config.image_analysis_endpoint)
        self.geo_client = GeoContextClient(endpoint=config.geo_context_endpoint)
        self.temporal_client = TemporalLogicClient(endpoint=config.temporal_logic_endpoint)
        self.crop_client = CropIntelligenceClient(endpoint=config.crop_intelligence_endpoint)
        self.data_client = DataIntegrationClient(endpoint=config.data_integration_endpoint)
        self.inventory_client = InventoryClient(endpoint=config.inventory_endpoint)
        self.security_client = SecurityAccessClient(endpoint=config.security_access_endpoint)
        self.orchestrator_client = OrchestratorClient(endpoint=config.orchestrator.endpoint)

        # Initialize feedback and events
        self.feedback_hooks = FeedbackHooks(storage_endpoint=config.feedback_storage_endpoint)
        self.event_emitter = (
            EventEmitter(
                feedback_endpoint=config.event_emission.feedback_endpoint,
                event_bus_endpoint=config.event_emission.event_bus_endpoint,
            )
            if config.event_emission.enabled
            else None
        )

        logger.info("AgroLLMPipeline initialized")

    async def process_request(self, raw_request: Dict[str, Any]) -> AgroLLMResponse:
        """Process farmer request through full pipeline.

        Args:
            raw_request: Raw request dictionary

        Returns:
            AgroLLMResponse
        """
        logger.info(f"Processing request for user={raw_request.get('user_id', 'unknown')}")

        error_context = {}

        try:
            # Step 1: Normalize input
            request = self.normalizer.normalize(raw_request)

            # Step 2: Validate request safety constraints
            request_violations = self.safety_engine.validate_request(request)
            if request_violations:
                blocking_violations = [
                    v for v in request_violations if v.severity.value == "blocking"
                ]
                if blocking_violations:
                    raise ValueError(
                        f"Request blocked by safety constraints: {blocking_violations}"
                    )
                # Log warnings but continue
                for violation in request_violations:
                    logger.warning(f"Request safety warning: {violation.message}")

            # Step 3: Retrieve context (RAG, KG, Local)
            rag_context = None
            kg_context = None
            local_context = None
            rag_failed = False

            if self.config.feature_flags.enable_rag:
                try:
                    retrieved_docs = await self.rag_adapter.retrieve_context(
                        query=request.text,
                        filters={"crop": request.crop.type if request.crop else None},
                    )
                    rag_context = {
                        "documents": [
                            {"id": doc.id, "content": doc.content, "score": doc.score}
                            for doc in retrieved_docs
                        ]
                    }
                except Exception as e:
                    logger.error(f"RAG retrieval failed: {e}")
                    rag_failed = True
                    error_context["rag_error"] = str(e)
                    if self.config.fallback.activate_on_rag_failure and self.fallback_engine:
                        return await self.fallback_engine.generate_fallback_response(
                            request, error_context
                        )

            if self.config.feature_flags.enable_kg:
                try:
                    kg_result = await self.kg_adapter.query(
                        {
                            "crop": request.crop.type if request.crop else None,
                            "region": request.geo.region_code,
                            "entity_types": ["crop", "disease", "pest"],
                        }
                    )
                    kg_context = {
                        "entities": kg_result.entities,
                        "relationships": kg_result.relationships,
                    }
                except Exception as e:
                    logger.error(f"KG query failed: {e}")
                    error_context["kg_error"] = str(e)

            if self.config.feature_flags.use_local:
                try:
                    local_context = self.local_adapter.get_context(
                        region_code=request.geo.region_code,
                        crop_variety=request.crop.variety if request.crop else None,
                    )
                except Exception as e:
                    logger.error(f"Local intelligence failed: {e}")
                    error_context["local_error"] = str(e)

            # Step 4: Fuse multi-modal inputs
            fused_context = self.fusion_engine.fuse(
                request=request,
                rag_context=rag_context,
                kg_context=kg_context,
                local_context=local_context,
            )

            # Step 5: Generate LLM response (with fallback on failure)
            try:
                raw_llm_output = await self.llm_wrapper.generate_response(
                    request=request, context=fused_context
                )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                error_context["llm_error"] = str(e)
                if self.config.fallback.activate_on_llm_failure and self.fallback_engine:
                    fallback_response = await self.fallback_engine.generate_fallback_response(
                        request, error_context
                    )
                    if self.event_emitter:
                        await self.event_emitter.emit_fallback_event(
                            request, self.config.fallback.mode, error_context
                        )
                    return fallback_response
                raise

            # Step 6: Validate reasoning graph
            reasoning_graph = self.reasoning_engine.validate_output(
                llm_output=raw_llm_output.model_dump(), request_context=fused_context
            )

            # Step 6b: Rewrite response if reasoning graph has violations
            if reasoning_graph.violations:
                raw_llm_output = self.reasoning_rewriter.rewrite_response(
                    raw_llm_output, reasoning_graph
                )

            # Step 7: Calibrate confidence
            confidence_factors = self.confidence_calibrator.extract_factors(
                llm_output=raw_llm_output.model_dump(),
                rag_context=rag_context,
                image_features=(
                    [
                        feat.model_dump() if hasattr(feat, "model_dump") else feat
                        for feat in request.image_features
                    ]
                    if request.image_features
                    else None
                ),
                request_context=fused_context,
            )

            base_confidence = raw_llm_output.diagnosis_card.confidence
            calibrated_confidence = self.confidence_calibrator.calibrate(
                base_confidence, confidence_factors, fused_context
            )
            raw_llm_output.diagnosis_card.confidence = calibrated_confidence

            # Step 8: Validate response safety constraints
            response_violations = self.safety_engine.validate_response(
                response=raw_llm_output, request=request
            )

            # Step 9: Validate temporal safety
            if self.temporal_safety_validator:
                temporal_violations = self.temporal_safety_validator.validate(
                    raw_llm_output, request
                )
                response_violations.extend(temporal_violations)

            # Handle blocking violations
            blocking_violations = [v for v in response_violations if v.severity.value == "blocking"]
            if blocking_violations:
                logger.error(f"Response blocked by safety constraints: {blocking_violations}")
                if self.event_emitter:
                    for violation in blocking_violations:
                        await self.event_emitter.emit_safety_event(
                            "blocking_violation", violation.__dict__, request, raw_llm_output
                        )
                raw_llm_output.diagnosis_card.warnings.extend(
                    [v.message for v in blocking_violations]
                )
                raw_llm_output.flags.constraint_violation = True

            # Add warnings from non-blocking violations
            for violation in response_violations:
                if violation.severity.value != "blocking":
                    raw_llm_output.diagnosis_card.warnings.append(violation.message)

            # Step 10: Post-process structured output (final safety pass)
            raw_llm_output, post_violations = self.safety_postprocessor.validate_and_fix(
                raw_llm_output, fused_context
            )

            # Step 11: Low-confidence routing to human review
            if calibrated_confidence < self.config.thresholds.low_confidence:
                raw_llm_output.flags.low_confidence = True
                if calibrated_confidence < self.config.thresholds.human_review_required:
                    raw_llm_output.flags.needs_review = True
                    if self.event_emitter:
                        await self.event_emitter.emit_low_confidence_event(
                            request,
                            raw_llm_output,
                            calibrated_confidence,
                            f"Confidence {calibrated_confidence:.2f} below threshold {self.config.thresholds.human_review_required}",
                        )

            # Step 12: Add reasoning graph to explainability
            raw_llm_output.explainability.reasoning_graph = {
                "nodes": [
                    {
                        "id": node.id,
                        "type": node.type,
                        "content": node.content,
                        "confidence": node.confidence,
                    }
                    for node in reasoning_graph.nodes
                ],
                "edges": [
                    {"from": e[0], "to": e[1], "relation": e[2]} for e in reasoning_graph.edges
                ],
                "violations": reasoning_graph.violations,
            }

            # Step 13: Emit events
            if self.event_emitter and self.config.event_emission.enabled:
                await self.event_emitter.emit_interaction_event(
                    request, raw_llm_output, {"pipeline_version": "v1"}
                )

            # Step 14: Save interaction for feedback/learning
            if self.config.feature_flags.enable_feedback:
                try:
                    await self.feedback_hooks.save_interaction(
                        request=request,
                        response=raw_llm_output,
                        metadata={"pipeline_version": "v1"},
                    )
                except Exception as e:
                    logger.error(f"Failed to save interaction: {e}")

            logger.info(f"Request processed successfully, response_id={raw_llm_output.id}")

            return raw_llm_output

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            error_context["pipeline_error"] = str(e)

            # Fallback on any critical error
            if self.fallback_engine and self.config.fallback.enabled:
                try:
                    fallback_response = await self.fallback_engine.generate_fallback_response(
                        raw_request if "request" not in locals() else request, error_context
                    )
                    if self.event_emitter:
                        await self.event_emitter.emit_fallback_event(
                            raw_request if "request" not in locals() else request,
                            self.config.fallback.mode,
                            error_context,
                        )
                    return fallback_response
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")

            raise
