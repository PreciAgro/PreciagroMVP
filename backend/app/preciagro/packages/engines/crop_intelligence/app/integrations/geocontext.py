from __future__ import annotations

from typing import Optional

from .http import BaseServiceClient


class GeoContextClient(BaseServiceClient):
    def fetch_soil(self, field_id: str, boundary_geojson: dict) -> Optional[dict]:
        payload = {"field_id": field_id, "geometry": boundary_geojson}
        return self._request("POST", "/geocontext/soil", json=payload)

    def fetch_climate(self, field_id: str, boundary_geojson: dict) -> Optional[dict]:
        payload = {"field_id": field_id, "geometry": boundary_geojson}
        return self._request("POST", "/geocontext/climate", json=payload)
