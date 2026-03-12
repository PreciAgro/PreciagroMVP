from __future__ import annotations

from typing import Optional

from .http import BaseServiceClient


class DataIntegrationClient(BaseServiceClient):
    def fetch_weather(self, field_id: str) -> Optional[dict]:
        payload = {"field_id": field_id}
        return self._request("POST", "/data/weather", json=payload)

    def fetch_market(self, crop: str, region: str | None = None) -> Optional[dict]:
        payload = {"crop": crop, "region": region}
        return self._request("POST", "/data/market", json=payload)
