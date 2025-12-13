from typing import Dict, Any

class TemporalClient:
    def __init__(self):
        pass

    def get_context(self, user_id: str) -> Dict[str, Any]:
        """
        Fetches crop stage and season data.
        """
        # Stub implementation
        return {
            "season": "Summer",
            "crop_stage": "Vegetative"
        }
