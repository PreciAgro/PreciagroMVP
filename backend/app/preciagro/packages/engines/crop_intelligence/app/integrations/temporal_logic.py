from __future__ import annotations

from typing import Optional

from .http import BaseServiceClient


class TemporalLogicClient(BaseServiceClient):
    def fetch_schedule(self, field_id: str) -> Optional[dict]:
        payload = {"field_id": field_id}
        return self._request("POST", "/temporal/schedule", json=payload)
