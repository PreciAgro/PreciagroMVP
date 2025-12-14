from typing import TypedDict, Optional, List


class Event(TypedDict, total=False):
    kind: str
    field_id: str
    payload: dict
