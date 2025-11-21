"""Session cache backed by Redis with in-memory fallback."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis


logger = logging.getLogger(__name__)


class SessionStore:
    """Persists lightweight session state such as recent intents."""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600) -> None:
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.redis: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    async def connect(self) -> None:
        """Attempt to connect to Redis; if it fails, stay in memory mode."""
        try:
            client = redis.from_url(self.redis_url, decode_responses=True)
            await client.ping()
            self.redis = client
            logger.info("SessionStore connected to Redis at %s", self.redis_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SessionStore using in-memory cache: %s", exc)
            self.redis = None

    async def get(self, session_id: str) -> Dict[str, Any]:
        """Retrieve session state."""
        if self.redis:
            data = await self.redis.get(session_id)
            if data:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("Failed to decode session payload; returning empty.")
        return self._memory_cache.get(session_id, {})

    async def set(self, session_id: str, state: Dict[str, Any]) -> None:
        """Persist session state."""
        if self.redis:
            await self.redis.set(session_id, json.dumps(state), ex=self.ttl_seconds)
        self._memory_cache[session_id] = state

    async def close(self) -> None:
        """Close Redis connection if one exists."""
        if self.redis:
            try:
                await self.redis.aclose()
            except Exception:  # noqa: BLE001
                logger.debug("Redis close raised but is non-fatal.", exc_info=True)
