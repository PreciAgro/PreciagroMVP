from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from ..core.config import settings


logger = logging.getLogger(__name__)


class BaseServiceClient:
    """Shared HTTP client wrapper with auth headers and retry shim."""

    def __init__(self, base_url: str | None):
        self.base_url = base_url.rstrip("/") if base_url else None
        self._timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.SERVICE_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {settings.SERVICE_AUTH_TOKEN}"
        return headers

    def _request(self, method: str, path: str, json: Optional[dict] = None) -> Optional[dict]:
        if not self.base_url:
            return None
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.request(method, url, json=json, headers=self._headers())
                resp.raise_for_status()
                if resp.content:
                    return resp.json()
        except httpx.HTTPError as exc:  # pragma: no cover - network side effects
            logger.warning("Service call failed %s %s: %s", method, url, exc)
        return None
