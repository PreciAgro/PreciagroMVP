"""Integration client for Diagnosis & Recommendation Engine."""

from __future__ import annotations

import httpx
from typing import Optional, Dict, Any

from ..core.config import settings


class DiagnosisRecommendationClient:
    """Client for interacting with Diagnosis & Recommendation Engine."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.DIAGNOSIS_RECOMMENDATION_URL
        self.client = httpx.AsyncClient(timeout=10.0) if self.base_url else None

    async def validate_recommendation(
        self, recommendation_id: str, required_items: list
    ) -> Optional[Dict[str, Any]]:
        """Validate a recommendation against inventory before execution.
        
        This method should be called by the Diagnosis & Recommendation Engine
        before executing any recommendation that requires inventory.
        """
        if not self.client:
            return None
        
        try:
            response = await self.client.post(
                f"{self.base_url}/recommendations/{recommendation_id}/validate-inventory",
                json={"required_items": required_items},
                headers={"X-PreciAgro-Token": settings.API_AUTH_TOKEN} if settings.API_AUTH_TOKEN else {},
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()

