"""Integration client for Crop Intelligence Engine."""

from __future__ import annotations

import httpx
from typing import Optional, Dict, Any

from ..core.config import settings


class CropIntelligenceClient:
    """Client for interacting with Crop Intelligence Engine."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.CROP_INTELLIGENCE_URL
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_field_info(self, field_id: str) -> Optional[Dict[str, Any]]:
        """Get field information including crop type and growth stage."""
        try:
            response = await self.client.get(
                f"{self.base_url}/cie/field/{field_id}",
                headers=(
                    {"X-PreciAgro-Token": settings.API_AUTH_TOKEN}
                    if settings.API_AUTH_TOKEN
                    else {}
                ),
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    async def get_crop_stage(self, field_id: str) -> Optional[str]:
        """Get current crop growth stage for a field."""
        field_info = await self.get_field_info(field_id)
        if field_info:
            # Extract growth stage from field state
            state = field_info.get("state", {})
            return state.get("stage")
        return None

    async def get_usage_rates(self, crop_type: str, crop_stage: str) -> Optional[Dict[str, float]]:
        """Get recommended usage rates for inputs based on crop and stage.

        Returns a dictionary mapping input categories to usage rates.
        For MVP, returns None (uses rule-based estimation).
        In production, this would query the Crop Intelligence Engine for
        agronomic rules and usage rates.
        """
        # MVP: Return None to use rule-based estimation
        # Production: Query Crop Intelligence Engine for agronomic rules
        return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
