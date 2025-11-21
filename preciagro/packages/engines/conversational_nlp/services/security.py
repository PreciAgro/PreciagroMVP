"""Simple auth and rate limiting helpers."""

from __future__ import annotations

import logging
import time
from typing import Dict

from fastapi import Depends, Header, HTTPException, status

from ..core.config import settings


logger = logging.getLogger(__name__)


class RateLimiter:
    """Naive, per-process rate limiter (token bucket) with 1-minute window."""

    def __init__(self, limit_per_minute: int) -> None:
        self.limit = max(limit_per_minute, 1)
        self.window_seconds = 60
        self.buckets: Dict[str, Dict[str, float]] = {}

    def check(self, key: str) -> None:
        now = time.time()
        bucket = self.buckets.get(key, {"tokens": float(self.limit), "ts": now})
        elapsed = now - bucket["ts"]
        # Refill tokens linearly
        bucket["tokens"] = min(
            float(self.limit), bucket["tokens"] + (elapsed / self.window_seconds) * self.limit
        )
        bucket["ts"] = now
        if bucket["tokens"] < 1.0:
            self.buckets[key] = bucket
            logger.warning("Rate limit exceeded for key=%s", key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        bucket["tokens"] -= 1.0
        self.buckets[key] = bucket


rate_limiter = RateLimiter(limit_per_minute=settings.rate_limit_per_minute)


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require API key when configured."""
    if not settings.inbound_api_key:
        return
    if x_api_key != settings.inbound_api_key:
        logger.warning("Invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


async def enforce_rate_limit(user_key: str | None = Header(default=None)) -> None:
    """Apply per-minute rate limiting keyed by user or fallback to IP header."""
    key = user_key or "anonymous"
    rate_limiter.check(key)
