"""Integration client for Temporal Logic Engine."""

from __future__ import annotations

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.config import settings


class TemporalLogicClient:
    """Client for interacting with Temporal Logic Engine."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.TEMPORAL_LOGIC_URL
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_scheduled_tasks(
        self, farmer_id: str, days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get scheduled tasks that may require inventory."""
        try:
            response = await self.client.get(
                f"{self.base_url}/temporal/schedule/{farmer_id}",
                params={"days_ahead": days_ahead},
                headers=(
                    {"X-PreciAgro-Token": settings.API_AUTH_TOKEN}
                    if settings.API_AUTH_TOKEN
                    else {}
                ),
            )
            if response.status_code == 200:
                return response.json().get("tasks", [])
        except Exception:
            pass
        return []

    async def notify_inventory_deduction(self, task_id: str, item_id: str, quantity: float) -> bool:
        """Notify Temporal Logic Engine that inventory was deducted for a task."""
        try:
            response = await self.client.post(
                f"{self.base_url}/temporal/tasks/{task_id}/inventory-deduction",
                json={
                    "item_id": item_id,
                    "quantity": quantity,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                headers=(
                    {"X-PreciAgro-Token": settings.API_AUTH_TOKEN}
                    if settings.API_AUTH_TOKEN
                    else {}
                ),
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
