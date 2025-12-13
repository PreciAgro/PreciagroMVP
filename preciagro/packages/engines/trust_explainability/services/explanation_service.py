"""Main Explanation Service.

Orchestrates the explanation generation pipeline:
evidence collection → strategy selection → explanation generation → 
confidence estimation → safety validation → trace composition.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from ..contracts.v1.schemas import (
    ExplanationRequest,
    ExplanationResponse,
    ExplanationArtifact,
    ModelInfo,
    ReasoningTrace,
)
from ..contracts.v1.enums import (
    ExplanationLevel,
    ExplanationStrategy,
    SafetyStatus,
)
from ..core.evidence_collector import EvidenceCollector
from ..core.explanation_router import ExplanationRouter
from ..core.confidence_estimator import ConfidenceEstimator
from ..core.safety_gate import SafetyGate
from ..core.reasoning_trace import ReasoningTraceBuilder, get_trace_store
from ..strategies.base import BaseExplainer
from ..strategies.cv_explainer import CVExplainer
from ..strategies.tabular_explainer import TabularExplainer
from ..strategies.rule_explainer import RuleExplainer
from ..strategies.llm_summarizer import LLMSummarizer
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class ExplanationService:
    """Main orchestration service for explanations.
    
    Coordinates all components to generate tiered explanations
    with confidence metrics and safety validation.
    """
    
    def __init__(self) -> None:
        """Initialize explanation service."""
        self.settings = get_settings()
        
        # Initialize core components
        self.evidence_collector = EvidenceCollector()
        self.router = ExplanationRouter()
        self.confidence_estimator = ConfidenceEstimator()
        self.safety_gate = SafetyGate()
        self.trace_builder = ReasoningTraceBuilder()
        
        # Initialize and register strategies
        self._register_strategies()
        
        logger.info("ExplanationService initialized")
    
    def _register_strategies(self) -> None:
        """Register available explanation strategies."""
        # Register all strategies
        self.router.register_strategy(ExplanationStrategy.CV, CVExplainer)
        self.router.register_strategy(ExplanationStrategy.TABULAR, TabularExplainer)
        self.router.register_strategy(ExplanationStrategy.RULE, RuleExplainer)
        self.router.register_strategy(ExplanationStrategy.LLM, LLMSummarizer)
        
        # Instantiate for direct access
        self._strategies: Dict[ExplanationStrategy, BaseExplainer] = {
            ExplanationStrategy.CV: CVExplainer(),
            ExplanationStrategy.TABULAR: TabularExplainer(),
            ExplanationStrategy.RULE: RuleExplainer(),
            ExplanationStrategy.LLM: LLMSummarizer(),
        }
    
    async def explain(
        self,
        request: ExplanationRequest
    ) -> ExplanationResponse:
        """Generate full explanation for a request.
        
        Args:
            request: Explanation request
            
        Returns:
            ExplanationResponse with tiered explanations
        """
        start_time = time.time()
        
        try:
            # 1. Collect evidence
            evidence = self.evidence_collector.collect(request)
            
            # 2. Route to appropriate strategy
            strategy_type = self.router.route(
                evidence, request.model_type
            )
            
            # 3. Generate explanations for requested levels
            explanations: List[ExplanationArtifact] = []
            farmer_explanation: Optional[str] = None
            expert_explanation: Optional[str] = None
            saliency_thumbnail: Optional[str] = None
            feature_importance: Optional[Dict[str, float]] = None
            
            strategy = self._strategies.get(strategy_type)
            if not strategy:
                strategy = self._strategies[ExplanationStrategy.LLM]
            
            for level in request.levels:
                artifact = strategy.explain(
                    evidence=evidence,
                    model_output=request.model_outputs,
                    level=level,
                    language=request.language
                )
                explanations.append(artifact)
                
                # Extract specific outputs
                if level == ExplanationLevel.FARMER:
                    farmer_explanation = artifact.content
                elif level == ExplanationLevel.EXPERT:
                    expert_explanation = artifact.content
                
                # Extract visual artifacts
                if artifact.structured_data:
                    if "saliency_thumbnail" in artifact.structured_data:
                        saliency_thumbnail = artifact.structured_data["saliency_thumbnail"]
                    if "feature_importance" in artifact.structured_data:
                        feature_importance = artifact.structured_data["feature_importance"]
            
            # 4. Estimate confidence
            confidence_metrics = None
            overall_confidence = 0.0
            confidence_level = "low"
            
            if request.include_confidence:
                confidence_metrics = self.confidence_estimator.estimate(
                    [request.model_outputs],
                    [ev.confidence for ev in evidence]
                )
                overall_confidence = confidence_metrics.overall_confidence
                confidence_level = self.confidence_estimator.get_confidence_level(
                    overall_confidence
                )
            
            # 5. Run safety gate
            safety_result = None
            safety_status = SafetyStatus.PASSED
            safety_warnings: List[str] = []
            
            if request.include_safety_check:
                safety_result = self.safety_gate.validate(
                    request.model_outputs,
                    request.context
                )
                safety_status = safety_result.status
                safety_warnings = [v.message for v in safety_result.violations]
            
            # 6. Build reasoning trace
            model_info = ModelInfo(
                model_id=request.model_id,
                model_name=request.model_id,
                model_version=request.model_outputs.get("model_version", "unknown"),
                model_type=request.model_type,
                confidence=overall_confidence
            )
            
            trace = (
                self.trace_builder
                .create(request.request_id)
                .add_input_ref("request", request.request_id)
                .add_model(model_info)
                .add_evidence(evidence)
                .add_explanations(explanations)
            )
            
            if confidence_metrics:
                trace.set_confidence(confidence_metrics)
            
            if safety_result:
                trace.set_safety_check(safety_result)
            
            reasoning_trace = trace.build()
            
            # 7. Store trace
            trace_store = get_trace_store()
            trace_store.store(reasoning_trace)
            
            # 8. Build response
            processing_time = (time.time() - start_time) * 1000
            
            response = ExplanationResponse(
                request_id=request.request_id,
                trace_id=reasoning_trace.trace_id,
                farmer_explanation=farmer_explanation,
                expert_explanation=expert_explanation,
                auditor_trace=reasoning_trace if ExplanationLevel.AUDITOR in request.levels else None,
                saliency_thumbnail=saliency_thumbnail,
                feature_importance=feature_importance,
                confidence=overall_confidence,
                confidence_level=confidence_level,
                safety_status=safety_status,
                safety_warnings=safety_warnings,
                feedback_url=f"/api/v1/feedback?trace_id={reasoning_trace.trace_id}",
                processing_time_ms=processing_time
            )
            
            logger.info(
                f"Generated explanation for request {request.request_id} "
                f"in {processing_time:.1f}ms (strategy: {strategy_type.value}, "
                f"confidence: {overall_confidence:.2f}, safety: {safety_status.value})"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}", exc_info=True)
            
            # Return minimal error response
            return ExplanationResponse(
                request_id=request.request_id,
                trace_id="error",
                farmer_explanation="We couldn't generate an explanation at this time. Please try again.",
                safety_status=SafetyStatus.WARNING,
                safety_warnings=["Explanation generation failed"],
                processing_time_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)}
            )
    
    async def explain_fast(
        self,
        request: ExplanationRequest
    ) -> str:
        """Generate fast one-liner explanation.
        
        Args:
            request: Explanation request
            
        Returns:
            One-line farmer-friendly explanation
        """
        # Use LLM summarizer for quick one-liner
        summarizer = self._strategies[ExplanationStrategy.LLM]
        return summarizer.generate_one_liner(
            request.model_outputs,
            request.language
        )
    
    async def explain_deep(
        self,
        trace_id: str
    ) -> Optional[ExplanationResponse]:
        """Retrieve deep explanation from stored trace.
        
        Args:
            trace_id: Reasoning trace ID
            
        Returns:
            ExplanationResponse or None if trace not found
        """
        trace_store = get_trace_store()
        trace = trace_store.get(trace_id)
        
        if not trace:
            return None
        
        # Reconstruct response from trace
        farmer_explanation = None
        expert_explanation = None
        saliency_thumbnail = None
        feature_importance = None
        
        for artifact in trace.explanations:
            if artifact.level == ExplanationLevel.FARMER:
                farmer_explanation = artifact.content
            elif artifact.level == ExplanationLevel.EXPERT:
                expert_explanation = artifact.content
            
            if artifact.structured_data:
                if "saliency_thumbnail" in artifact.structured_data:
                    saliency_thumbnail = artifact.structured_data["saliency_thumbnail"]
                if "feature_importance" in artifact.structured_data:
                    feature_importance = artifact.structured_data["feature_importance"]
        
        confidence = trace.confidence.overall_confidence if trace.confidence else 0.0
        confidence_level = self.confidence_estimator.get_confidence_level(confidence)
        
        safety_status = trace.safety_check.status if trace.safety_check else SafetyStatus.PASSED
        safety_warnings = [
            v.message for v in (trace.safety_check.violations if trace.safety_check else [])
        ]
        
        return ExplanationResponse(
            request_id=trace.request_id,
            trace_id=trace.trace_id,
            farmer_explanation=farmer_explanation,
            expert_explanation=expert_explanation,
            auditor_trace=trace,
            saliency_thumbnail=saliency_thumbnail,
            feature_importance=feature_importance,
            confidence=confidence,
            confidence_level=confidence_level,
            safety_status=safety_status,
            safety_warnings=safety_warnings,
            feedback_url=trace.feedback_url
        )
    
    def get_supported_strategies(self) -> List[str]:
        """Get list of supported explanation strategies.
        
        Returns:
            List of strategy names
        """
        return [s.value for s in self._strategies.keys()]
