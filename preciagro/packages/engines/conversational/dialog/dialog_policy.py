from typing import Dict, Any, Optional

class DialogPolicy:
    def __init__(self):
        pass

    def determine_action(self, user_input: str, agrollm_response: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines the next action based on user input and AgroLLM response.
        """
        flags = agrollm_response.get("flags", {})
        
        # 1. Force human review if flagged
        if flags.get("needs_review"):
            return {
                "action": "human_handoff",
                "reason": "AgroLLM flagged for review"
            }

        # 2. Handle low confidence
        if flags.get("low_confidence"):
            return {
                "action": "fallback",
                "response": "I'm not entirely sure about that. Could you provide more details?"
            }

        # 3. Check for missing information (Clarification)
        if agrollm_response.get("missing_slots"):
            return {
                "action": "clarify",
                "slots": agrollm_response["missing_slots"]
            }

        # 4. Check for risky actions requiring confirmation
        if flags.get("high_risk"):
            return {
                "action": "confirm_risk",
                "details": agrollm_response.get("risk_details")
            }

        # Default: Proceed with response
        return {
            "action": "respond",
            "content": agrollm_response.get("content")
        }
