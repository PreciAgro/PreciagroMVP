"""NLP adapter interface for future NLP model integration."""

from typing import Dict, Any, Optional
from .base import BaseAdapter


class NLPAdapter(BaseAdapter):
    """Adapter for NLP models (symptom extraction, intent classification)."""
    
    def is_available(self) -> bool:
        """Check if NLP model is available."""
        # Stub: return False until model is integrated
        return False
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process text data through NLP model.
        
        Args:
            input_data: Dict with 'text', 'context', 'metadata'
            
        Returns:
            Dict with 'symptoms', 'entities', 'intent', 'confidence'
        """
        if not self.is_available():
            return {
                "symptoms": [],
                "entities": {},
                "intent": "unknown",
                "confidence": 0.0,
                "error": "NLP adapter not available",
            }
        
        # TODO: Integrate actual NLP model
        # Example:
        # model = load_nlp_model(self.config.get("model_path"))
        # results = model.extract_symptoms(input_data["text"])
        # return format_nlp_results(results)
        
        return {
            "symptoms": [],
            "entities": {},
            "intent": "unknown",
            "confidence": 0.0,
        }

