"""Confidence Calibration Logic - Deterministic confidence estimation."""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFactors:
    """Factors contributing to confidence score."""
    
    cv_detection_score: float = 0.0  # Computer vision detection confidence
    retrieval_score: float = 0.0      # RAG retrieval relevance score
    rule_violations: int = 0          # Number of rule violations
    known_pattern_match: float = 0.0  # Match to known patterns
    data_completeness: float = 0.0    # Completeness of input data
    model_uncertainty: float = 0.0    # Model's own uncertainty estimate


class ConfidenceCalibrator:
    """Calibrates confidence scores based on multiple factors."""
    
    def __init__(
        self,
        cv_weight: float = 0.2,
        retrieval_weight: float = 0.2,
        rule_weight: float = 0.2,
        pattern_weight: float = 0.2,
        completeness_weight: float = 0.1,
        model_weight: float = 0.1
    ):
        """Initialize confidence calibrator.
        
        Args:
            cv_weight: Weight for CV detection score
            retrieval_weight: Weight for retrieval score
            rule_weight: Weight for rule violations (negative)
            pattern_weight: Weight for known pattern match
            completeness_weight: Weight for data completeness
            model_weight: Weight for model uncertainty
        """
        self.cv_weight = cv_weight
        self.retrieval_weight = retrieval_weight
        self.rule_weight = rule_weight
        self.pattern_weight = pattern_weight
        self.completeness_weight = completeness_weight
        self.model_weight = model_weight
        
        # Normalize weights
        total = sum([
            cv_weight, retrieval_weight, rule_weight,
            pattern_weight, completeness_weight, model_weight
        ])
        if total > 0:
            self.cv_weight /= total
            self.retrieval_weight /= total
            self.rule_weight /= total
            self.pattern_weight /= total
            self.completeness_weight /= total
            self.model_weight /= total
        
        logger.info("ConfidenceCalibrator initialized")
    
    def calibrate(
        self,
        base_confidence: float,
        factors: ConfidenceFactors,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calibrate confidence score.
        
        Args:
            base_confidence: Base confidence from LLM (0.0-1.0)
            factors: Confidence factors
            context: Additional context
            
        Returns:
            Calibrated confidence (0.0-1.0)
        """
        # Start with base confidence
        calibrated = base_confidence
        
        # Apply CV detection score (if available)
        if factors.cv_detection_score > 0:
            calibrated += self.cv_weight * factors.cv_detection_score
            calibrated = min(1.0, calibrated)
        
        # Apply retrieval score
        if factors.retrieval_score > 0:
            calibrated += self.retrieval_weight * factors.retrieval_score
            calibrated = min(1.0, calibrated)
        
        # Penalize for rule violations
        if factors.rule_violations > 0:
            penalty = min(0.3, factors.rule_violations * 0.1)
            calibrated -= penalty
            calibrated = max(0.0, calibrated)
        
        # Apply known pattern match
        if factors.known_pattern_match > 0:
            calibrated += self.pattern_weight * factors.known_pattern_match
            calibrated = min(1.0, calibrated)
        
        # Apply data completeness
        if factors.data_completeness > 0:
            calibrated += self.completeness_weight * factors.data_completeness
            calibrated = min(1.0, calibrated)
        
        # Apply model uncertainty (negative correlation)
        if factors.model_uncertainty > 0:
            calibrated -= self.model_weight * factors.model_uncertainty
            calibrated = max(0.0, calibrated)
        
        # Ensure bounds
        calibrated = max(0.0, min(1.0, calibrated))
        
        logger.debug(
            f"Confidence calibrated: {base_confidence:.2f} -> {calibrated:.2f} "
            f"(factors: cv={factors.cv_detection_score:.2f}, "
            f"retrieval={factors.retrieval_score:.2f}, "
            f"violations={factors.rule_violations})"
        )
        
        return calibrated
    
    def extract_factors(
        self,
        llm_output: Dict[str, Any],
        rag_context: Optional[Dict[str, Any]] = None,
        image_features: Optional[List[Dict[str, Any]]] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> ConfidenceFactors:
        """Extract confidence factors from context.
        
        Args:
            llm_output: LLM output dictionary
            rag_context: RAG retrieval context
            image_features: Image feature detections
            request_context: Original request context
            
        Returns:
            ConfidenceFactors
        """
        factors = ConfidenceFactors()
        
        # Extract CV detection score from image features
        if image_features:
            cv_scores = [
                feat.get("confidence", 0.0) or 0.0
                for feat in image_features
                if isinstance(feat, dict) and "confidence" in feat
            ]
            if cv_scores:
                factors.cv_detection_score = sum(cv_scores) / len(cv_scores)
        
        # Extract retrieval score from RAG context
        if rag_context and "documents" in rag_context:
            scores = [
                doc.get("score", 0.0) or 0.0
                for doc in rag_context["documents"]
                if isinstance(doc, dict) and "score" in doc
            ]
            if scores:
                factors.retrieval_score = sum(scores) / len(scores)
        
        # Count rule violations
        if "violations" in llm_output:
            factors.rule_violations = len(llm_output["violations"])
        elif "reasoning_graph" in llm_output:
            reasoning_graph = llm_output.get("reasoning_graph", {})
            if isinstance(reasoning_graph, dict):
                factors.rule_violations = len(reasoning_graph.get("violations", []))
        
        # Calculate data completeness
        if request_context:
            completeness_score = self._calculate_completeness(request_context)
            factors.data_completeness = completeness_score
        
        # Extract model uncertainty (if provided)
        if "uncertainty" in llm_output:
            factors.model_uncertainty = float(llm_output["uncertainty"])
        elif "confidence_breakdown" in llm_output:
            # Use inverse of average confidence as uncertainty
            breakdown = llm_output["confidence_breakdown"]
            if isinstance(breakdown, dict) and breakdown:
                avg_confidence = sum(breakdown.values()) / len(breakdown)
                factors.model_uncertainty = 1.0 - avg_confidence
        
        # Calculate known pattern match (simplified)
        factors.known_pattern_match = self._calculate_pattern_match(
            llm_output, request_context
        )
        
        return factors
    
    def _calculate_completeness(self, request_context: Dict[str, Any]) -> float:
        """Calculate data completeness score."""
        required_fields = ["text", "geo"]
        optional_fields = ["soil", "crop", "weather", "images"]
        
        completeness = 0.0
        
        # Required fields (50% weight)
        required_present = sum(1 for field in required_fields if field in request_context)
        completeness += 0.5 * (required_present / len(required_fields))
        
        # Optional fields (50% weight)
        optional_present = sum(1 for field in optional_fields if field in request_context)
        completeness += 0.5 * (optional_present / len(optional_fields))
        
        return completeness
    
    def _calculate_pattern_match(
        self,
        llm_output: Dict[str, Any],
        request_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate match to known patterns."""
        # Simplified pattern matching
        # In production, this would use a pattern database
        
        known_problems = [
            "yellow leaves", "brown spots", "wilting", "pest damage",
            "disease", "nutrient deficiency", "water stress"
        ]
        
        problem_text = llm_output.get("diagnosis", {}).get("problem", "").lower()
        if not problem_text:
            problem_text = llm_output.get("text", "").lower()
        
        matches = sum(1 for pattern in known_problems if pattern in problem_text)
        
        # Normalize to 0-1
        return min(1.0, matches / len(known_problems))








