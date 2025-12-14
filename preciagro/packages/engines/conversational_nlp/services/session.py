"""Session cache backed by Redis with in-memory fallback."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

from ..models import SessionContext, SessionTurn

logger = logging.getLogger(__name__)


class SessionStore:
    """Persists lightweight session state such as recent intents."""

    def __init__(
        self,
        redis_url: str,
        ttl_seconds: int = 3600,
        max_turns: int = 6,
        history_enabled: bool = True,
        retention_hours: int = 24,
    ) -> None:
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self.history_enabled = history_enabled
        self.retention_seconds = max(retention_hours * 3600, ttl_seconds)
        self.redis: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, Dict] = {}

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

    async def get(self, session_id: str, user_id: str) -> SessionContext:
        """Retrieve session state."""
        raw: Optional[Dict] = None
        if self.redis:
            data = await self.redis.get(session_id)
            if data:
                try:
                    raw = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("Failed to decode session payload; returning empty.")
        if raw is None:
            raw = self._memory_cache.get(session_id)
        if raw:
            try:
                return SessionContext(**raw)
            except Exception:  # noqa: BLE001
                logger.warning("Session payload invalid; resetting context.")
        return SessionContext(session_id=session_id, user_id=user_id)

    def append_turn(
        self,
        context: SessionContext,
        role: str,
        text: str,
        intent: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a turn to the rolling history."""
        if not self.history_enabled:
            return
        turn = SessionTurn(
            role=role,  # type: ignore[arg-type]
            text=text,
            intent=intent,
            metadata=metadata or {},
        )
        context.turns.append(turn)
        if len(context.turns) > self.max_turns:
            context.turns = context.turns[-self.max_turns :]

    async def save(self, context: SessionContext) -> None:
        """Persist session state."""
        if not self.history_enabled:
            context.turns = []
        payload = context.model_dump()
        self._memory_cache[context.session_id] = payload
        if self.redis:
            await self.redis.set(
                context.session_id,
                json.dumps(payload),
                ex=self.retention_seconds,
            )

    async def delete(self, session_id: str) -> None:
        """Remove a session from Redis/memory."""
        self._memory_cache.pop(session_id, None)
        if self.redis:
            await self.redis.delete(session_id)

    async def close(self) -> None:
        """Close Redis connection if one exists."""
        if self.redis:
            try:
                await self.redis.aclose()
            except Exception:  # noqa: BLE001
                logger.debug("Redis close raised but is non-fatal.", exc_info=True)
