"""Fail-Safe Fallback Engine - Rule-based fallback when LLM/RAG/APIs fail."""

import logging
from typing import Dict, Any, Optional
from enum import Enum

from ..contracts.v1.schemas import (
    FarmerRequest, AgroLLMResponse, DiagnosisCard,
    RecommendedAction, Explainability, ResponseFlags
)

logger = logging.getLogger(__name__)


class FallbackMode(str, Enum):
    """Fallback mode."""
    
    NONE = "none"  # No fallback
    BASIC = "basic"  # Basic rule-based responses
    SAFE_DEFAULT = "safe_default"  # Safe default recommendations


class FallbackEngine:
    """Rule-based fallback when primary systems fail."""
    
    def __init__(self, mode: FallbackMode = FallbackMode.BASIC):
        """Initialize fallback engine.
        
        Args:
            mode: Fallback mode
        """
        self.mode = mode
        logger.info(f"FallbackEngine initialized (mode={mode})")
    
    def generate_fallback_response(
        self,
        request: FarmerRequest,
        error_context: Optional[Dict[str, Any]] = None
    ) -> AgroLLMResponse:
        """Generate fallback response.
        
        Args:
            request: Original request
            error_context: Context about what failed
            
        Returns:
            Fallback AgroLLMResponse
        """
        logger.warning(f"Generating fallback response (mode={self.mode})")
        
        if self.mode == FallbackMode.BASIC:
            return self._generate_basic_fallback(request, error_context)
        elif self.mode == FallbackMode.SAFE_DEFAULT:
            return self._generate_safe_default(request, error_context)
        else:
            raise ValueError(f"Unknown fallback mode: {self.mode}")
    
    def _generate_basic_fallback(
        self,
        request: FarmerRequest,
        error_context: Optional[Dict[str, Any]]
    ) -> AgroLLMResponse:
        """Generate basic rule-based fallback."""
        # Extract key information
        crop_type = request.crop.type if request.crop else "crop"
        problem_text = request.text.lower()
        
        # Simple pattern matching for common problems
        diagnosis = "General agricultural issue detected"
        actions = []
        warnings = [
            "This is a fallback response. Please consult with an agricultural expert for detailed advice."
        ]
        
        # Basic rule-based diagnosis
        if "yellow" in problem_text and "leaf" in problem_text:
            diagnosis = f"Yellow leaves detected in {crop_type}. Possible causes: nutrient deficiency, water stress, or disease."
            actions = [
                RecommendedAction(
                    action="Check soil pH and nutrient levels",
                    priority="high"
                ),
                RecommendedAction(
                    action="Inspect for signs of disease or pests",
                    priority="medium"
                ),
                RecommendedAction(
                    action="Review irrigation schedule",
                    priority="medium"
                )
            ]
        elif "pest" in problem_text or "insect" in problem_text:
            diagnosis = f"Pest or insect issue detected in {crop_type}."
            actions = [
                RecommendedAction(
                    action="Identify the specific pest",
                    priority="high"
                ),
                RecommendedAction(
                    action="Consult local agricultural extension for pest management options",
                    priority="high"
                )
            ]
            warnings.append("Use pesticides only as a last resort and follow safety guidelines.")
        elif "disease" in problem_text:
            diagnosis = f"Disease symptoms detected in {crop_type}."
            actions = [
                RecommendedAction(
                    action="Identify the specific disease",
                    priority="high"
                ),
                RecommendedAction(
                    action="Remove affected plants if disease is severe",
                    priority="medium"
                ),
                RecommendedAction(
                    action="Consult agricultural expert for treatment options",
                    priority="high"
                )
            ]
        else:
            # Generic fallback
            actions = [
                RecommendedAction(
                    action="Consult with local agricultural extension service",
                    priority="high"
                ),
                RecommendedAction(
                    action="Review crop management practices",
                    priority="medium"
                )
            ]
        
        # Build response
        diagnosis_card = DiagnosisCard(
            problem=diagnosis,
            confidence=0.3,  # Low confidence for fallback
            severity="medium",
            evidence=[],
            recommended_actions=actions,
            warnings=warnings,
            citations=[],
            metadata={
                "fallback_mode": self.mode.value,
                "error_context": error_context or {}
            }
        )
        
        explainability = Explainability(
            rationales=[
                "This response was generated using basic rule-based fallback due to system limitations.",
                "For accurate diagnosis, please provide more details or consult an expert."
            ]
        )
        
        flags = ResponseFlags(
            low_confidence=True,
            needs_review=True,
            safety_warning=True
        )
        
        return AgroLLMResponse(
            generated_text=(
                f"I've detected an issue with your {crop_type}. "
                f"{diagnosis} "
                "However, this is a basic fallback response. "
                "Please consult with an agricultural expert for detailed, accurate advice."
            ),
            diagnosis_card=diagnosis_card,
            explainability=explainability,
            flags=flags,
            metadata={"fallback": True, "mode": self.mode.value}
        )
    
    def _generate_safe_default(
        self,
        request: FarmerRequest,
        error_context: Optional[Dict[str, Any]]
    ) -> AgroLLMResponse:
        """Generate safe default response."""
        crop_type = request.crop.type if request.crop else "crop"
        
        diagnosis_card = DiagnosisCard(
            problem="Unable to provide specific diagnosis. Please consult agricultural expert.",
            confidence=0.1,
            severity="low",
            evidence=[],
            recommended_actions=[
                RecommendedAction(
                    action="Contact local agricultural extension service",
                    priority="high"
                )
            ],
            warnings=[
                "System is currently unavailable. This is a safe default response.",
                "Do not take action based solely on this response."
            ],
            citations=[],
            metadata={"fallback": True, "mode": "safe_default"}
        )
        
        explainability = Explainability(
            rationales=[
                "System encountered an error and cannot provide detailed analysis.",
                "Safe default response to prevent harmful actions."
            ]
        )
        
        flags = ResponseFlags(
            low_confidence=True,
            needs_review=True,
            safety_warning=True
        )
        
        return AgroLLMResponse(
            generated_text=(
                "I'm unable to provide a detailed analysis at this time. "
                "Please consult with a qualified agricultural expert for advice on your crop."
            ),
            diagnosis_card=diagnosis_card,
            explainability=explainability,
            flags=flags,
            metadata={"fallback": True, "mode": "safe_default"}
        )








