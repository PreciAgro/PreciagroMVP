from typing import Dict, Any

class GeoClient:
    def __init__(self):
        pass

    def get_context(self, user_id: str) -> Dict[str, Any]:
        """
        Fetches location and region data for the user.
        """
        # Stub implementation
        return {
            "region": "Midwest",
            "soil_type": "Loam",
            "weather": "Sunny, 25C"
        }
