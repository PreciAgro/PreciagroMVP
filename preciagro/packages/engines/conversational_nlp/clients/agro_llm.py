"""HTTP client wrapper for AgroLLM service."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class AgroLLMClient:
    """Lightweight HTTP client for AgroLLM endpoints."""

    def __init__(self, url: str, api_key: str = "", timeout_seconds: float = 15.0):
        self.url = url.rstrip("/") if url else ""
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        """Return True when a URL is configured."""
        return bool(self.url)

    async def _post(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("AgroLLM request failed: %s", exc)
            return None

    async def classify(self, prompt: str, schema_version: str = "v0") -> Optional[Dict[str, Any]]:
        """Call AgroLLM intent classifier endpoint."""
        payload = {"prompt": prompt, "schema_version": schema_version}
        return await self._post(payload)

    async def generate(self, prompt: str, temperature: float = 0.2) -> Optional[str]:
        """Call AgroLLM generation endpoint and return plain text."""
        payload = {"prompt": prompt, "temperature": temperature}
        data = await self._post(payload)
        if not data:
            return None
        # Flexible key extraction for different backends
        for key in ("text", "output", "answer"):
            if key in data:
                return str(data[key])
        return None
