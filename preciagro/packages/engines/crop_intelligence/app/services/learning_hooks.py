from __future__ import annotations
from ..repos.events import repo


class LearningHooks:
    """Captures events for Product Insights Engine (PIE) learning loop."""

    def emit(self, kind: str, field_id: str, payload: dict) -> None:
        """Emit an event to the learning system.

        Args:
            kind: Event type
            field_id: Field identifier
            payload: Event payload data
        """
        repo.append({"kind": kind, "field_id": field_id, "payload": payload})


lh = LearningHooks()
