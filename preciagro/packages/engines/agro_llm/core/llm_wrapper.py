"""Core LLM Wrapper for AgroLLM Engine."""

import json
import logging
from typing import Optional, Dict, Any, Literal
from enum import Enum

from ..contracts.v1.schemas import FarmerRequest, AgroLLMResponse

logger = logging.getLogger(__name__)


class LLMMode(str, Enum):
    """LLM deployment mode."""
    
    PRETRAINED = "pretrained"
    SELF_HOSTED = "self_hosted"
    FUTURE_FINETUNED = "future_finetuned"


class AgroLLMWrapper:
    """Wrapper for the main LLM with mode switching support."""
    
    def __init__(
        self,
        mode: LLMMode = LLMMode.PRETRAINED,
        model_name: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """Initialize LLM wrapper.
        
        Args:
            mode: LLM deployment mode
            model_name: Model identifier
            api_endpoint: API endpoint for self-hosted models
            api_key: API key if required
            **kwargs: Additional configuration
        """
        self.mode = mode
        self.model_name = model_name or "agrollm-pretrained-v1"
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.config = kwargs
        
        logger.info(f"AgroLLMWrapper initialized with mode={mode}, model={self.model_name}")
    
    async def generate_response(
        self,
        request: FarmerRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> AgroLLMResponse:
        """Generate response from LLM.
        
        Args:
            request: Farmer request
            context: Additional context (RAG, KG, etc.)
            
        Returns:
            AgroLLMResponse with generated content
        """
        logger.info(f"Generating response for user={request.user_id}, mode={self.mode}")
        
        # Build prompt from request and context
        prompt = self._build_prompt(request, context or {})
        
        # Generate based on mode
        if self.mode == LLMMode.PRETRAINED:
            raw_output = await self._generate_pretrained(prompt)
        elif self.mode == LLMMode.SELF_HOSTED:
            raw_output = await self._generate_self_hosted(prompt)
        elif self.mode == LLMMode.FUTURE_FINETUNED:
            raw_output = await self._generate_finetuned(prompt)
        else:
            raise ValueError(f"Unknown LLM mode: {self.mode}")
        
        # Parse and structure output
        structured_output = self._parse_output(raw_output, request)
        
        return structured_output
    
    def _build_prompt(self, request: FarmerRequest, context: Dict[str, Any]) -> str:
        """Build prompt from request and context."""
        prompt_parts = [
            "You are an agricultural expert assistant providing advice to farmers.",
            f"Language: {request.language}",
            f"Location: {request.geo.region_code} (lat: {request.geo.lat}, lon: {request.geo.lon})",
        ]
        
        if request.crop:
            prompt_parts.append(f"Crop: {request.crop.type} ({request.crop.variety})")
        
        if request.soil:
            prompt_parts.append(f"Soil: pH={request.soil.pH}, moisture={request.soil.moisture}%")
        
        if request.weather:
            prompt_parts.append(f"Weather: temp={request.weather.temp}°C, humidity={request.weather.humidity}%")
        
        if context.get("rag_context"):
            prompt_parts.append(f"\nRelevant context:\n{context['rag_context']}")
        
        if context.get("kg_context"):
            prompt_parts.append(f"\nKnowledge graph context:\n{context['kg_context']}")
        
        prompt_parts.append(f"\nFarmer question: {request.text}")
        prompt_parts.append("\nProvide a structured response with diagnosis and recommendations.")
        
        return "\n".join(prompt_parts)
    
    async def _generate_pretrained(self, prompt: str) -> Dict[str, Any]:
        """Generate using pretrained model (placeholder)."""
        # TODO: Integrate with actual pretrained model API
        logger.warning("Using placeholder pretrained model")
        
        return {
            "text": "This is a placeholder response from the pretrained AgroLLM model. "
                   "The model will be integrated in the next phase.",
            "diagnosis": {
                "problem": "Placeholder diagnosis",
                "confidence": 0.5,
                "severity": "medium",
                "evidence": [],
                "actions": [],
                "warnings": ["This is a placeholder response"],
                "citations": []
            },
            "rationales": ["Placeholder reasoning"]
        }
    
    async def _generate_self_hosted(self, prompt: str) -> Dict[str, Any]:
        """Generate using self-hosted model (placeholder)."""
        # TODO: Integrate with self-hosted model endpoint
        logger.warning("Using placeholder self-hosted model")
        
        return await self._generate_pretrained(prompt)
    
    async def _generate_finetuned(self, prompt: str) -> Dict[str, Any]:
        """Generate using finetuned model (placeholder)."""
        # TODO: Integrate with finetuned model
        logger.warning("Using placeholder finetuned model")
        
        return await self._generate_pretrained(prompt)
    
    def _parse_output(self, raw_output: Dict[str, Any], request: FarmerRequest) -> AgroLLMResponse:
        """Parse raw LLM output into structured response."""
        from ..contracts.v1.schemas import (
            DiagnosisCard, RecommendedAction, Explainability, ResponseFlags
        )
        
        diagnosis_data = raw_output.get("diagnosis", {})
        
        diagnosis_card = DiagnosisCard(
            problem=diagnosis_data.get("problem", "No specific problem identified"),
            confidence=diagnosis_data.get("confidence", 0.5),
            severity=diagnosis_data.get("severity", "medium"),
            evidence=diagnosis_data.get("evidence", []),
            recommended_actions=[
                RecommendedAction(**action) if isinstance(action, dict) else RecommendedAction(action=str(action))
                for action in diagnosis_data.get("actions", [])
            ],
            warnings=diagnosis_data.get("warnings", []),
            citations=diagnosis_data.get("citations", []),
            metadata={"model_version": self.model_name}
        )
        
        explainability = Explainability(
            rationales=raw_output.get("rationales", [])
        )
        
        flags = ResponseFlags(
            low_confidence=diagnosis_card.confidence < 0.6,
            needs_review=diagnosis_card.severity == "high"
        )
        
        return AgroLLMResponse(
            generated_text=raw_output.get("text", ""),
            diagnosis_card=diagnosis_card,
            explainability=explainability,
            flags=flags
        )








