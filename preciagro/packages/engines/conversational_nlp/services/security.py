"""Simple auth and rate limiting helpers."""

from __future__ import annotations

import logging
import time
from typing import Dict

from fastapi import Header, HTTPException, status

from ..core.config import settings
from ..models import ErrorCode

logger = logging.getLogger(__name__)


class RateLimiter:
    """Naive, per-process rate limiter (token bucket) with 1-minute window."""

    def __init__(self, user_limit: int, tenant_limit: int) -> None:
        self.user_limit = max(user_limit, 1)
        self.tenant_limit = max(tenant_limit, 1)
        self.window_seconds = 60
        self.buckets: Dict[str, Dict[str, float]] = {}

    def _check(self, key: str, limit: int) -> None:
        now = time.time()
        bucket = self.buckets.get(key, {"tokens": float(limit), "ts": now})
        elapsed = now - bucket["ts"]
        bucket["tokens"] = min(float(limit), bucket["tokens"] + (elapsed / self.window_seconds) * limit)
        bucket["ts"] = now
        if bucket["tokens"] < 1.0:
            self.buckets[key] = bucket
            logger.warning("Rate limit exceeded for key=%s", key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "status": "error",
                    "errors": [
                        {"code": ErrorCode.RATE_LIMITED.value, "message": "Rate limit exceeded", "component": "rate_limit"}
                    ],
                },
            )
        bucket["tokens"] -= 1.0
        self.buckets[key] = bucket

    def enforce(self, tenant_id: str, user_id: str) -> None:
        self._check(f"user::{tenant_id}::{user_id}", self.user_limit)
        self._check(f"tenant::{tenant_id}", self.tenant_limit)


rate_limiter = RateLimiter(
    user_limit=settings.rate_limit_per_minute,
    tenant_limit=settings.tenant_rate_limit_per_minute,
)


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


async def require_admin_access(x_admin_api_key: str | None = Header(default=None)) -> None:
    """Protect admin routes with DEBUG_MODE and admin token."""
    if not settings.debug_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin routes disabled",
        )
    expected = settings.admin_api_key or settings.inbound_api_key
    if expected and x_admin_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )
    if not expected:
        logger.warning("Admin route accessed without ADMIN_API_KEY configured")


def enforce_rate_limit(tenant_id: str, user_id: str) -> None:
    """Apply per-minute rate limiting keyed by tenant + user."""
    tenant = tenant_id or "anonymous-tenant"
    user = user_id or "anonymous-user"
    rate_limiter.enforce(tenant, user)
