from typing import Dict, Any, Generator

class AgroLLMClient:
    def __init__(self):
        pass

    def generate_response(self, prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls AgroLLM to generate a response.
        Ensures 'model_mode: pretrained' is respected.
        """
        if prompt_payload.get("model_mode") != "pretrained":
            raise ValueError("AgroLLM Client only supports 'pretrained' mode.")

        # Simulate AgroLLM response
        return {
            "content": "This is a simulated response from AgroLLM.",
            "structured_output": {},
            "flags": {
                "needs_review": False,
                "low_confidence": False,
                "high_risk": False
            }
        }

    def stream_response(self, prompt_payload: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """
        Streams tokens from AgroLLM.
        """
        if prompt_payload.get("model_mode") != "pretrained":
            raise ValueError("AgroLLM Client only supports 'pretrained' mode.")

        # Simulate streaming
        tokens = ["This", " is", " a", " streamed", " response", "."]
        for token in tokens:
            yield {
                "token": token,
                "model_mode": "pretrained"
            }
