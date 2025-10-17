from __future__ import annotations
from typing import Dict, List
from .typing import Event

class EventRepo:
    """Storage abstraction — initially in-memory; replace with Postgres later."""
    
    def __init__(self):
        self._events: List[Event] = []

    def append(self, ev: Event) -> None:
        self._events.append(ev)

    def list_by_field(self, field_id: str) -> List[Event]:
        return [e for e in self._events if e["field_id"] == field_id]

repo = EventRepo()
