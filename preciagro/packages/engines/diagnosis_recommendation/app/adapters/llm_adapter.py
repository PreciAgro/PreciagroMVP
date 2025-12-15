"""LLM adapter interface for future LLM model integration."""

from typing import Dict, Any, Optional
from .base import BaseAdapter


class LLMAdapter(BaseAdapter):
    """Adapter for Large Language Models (hypothesis generation, reasoning)."""

    def is_available(self) -> bool:
        """Check if LLM is available."""
        # Stub: return False until model is integrated
        return False

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data through LLM.

        Args:
            input_data: Dict with 'prompt', 'context', 'observations', 'metadata'

        Returns:
            Dict with 'hypotheses', 'reasoning', 'confidence'
        """
        if not self.is_available():
            return {
                "hypotheses": [],
                "reasoning": "",
                "confidence": 0.0,
                "error": "LLM adapter not available",
            }

        # TODO: Integrate actual LLM
        # Example:
        # llm = load_llm(self.config.get("model_name"))
        # prompt = build_prompt(input_data)
        # response = llm.generate(prompt)
        # return format_llm_response(response)

        return {
            "hypotheses": [],
            "reasoning": "",
            "confidence": 0.0,
        }
