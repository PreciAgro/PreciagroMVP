from typing import Dict, Any


class FeedbackClient:
    def __init__(self):
        pass

    def emit_event(self, event_type: str, payload: Dict[str, Any]):
        """
        Emits an interaction event downstream.
        """
        # Stub implementation: Log to console or file
        print(f"Event Emitted: {event_type} - {payload}")
