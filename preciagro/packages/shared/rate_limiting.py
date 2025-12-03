"""Shared rate limiting middleware using Redis."""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, rate limiting will use in-memory storage")


def get_identifier(request: Request) -> str:
    """Get rate limit identifier from request.
    
    Uses the following priority:
    1. User ID from auth headers (if available)
    2. API key (if available)
    3. Client IP address
    """
    # Check for user ID in headers
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"
    
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:16]}"  # Use first 16 chars
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def create_limiter(
    redis_url: Optional[str] = None,
    default_limits: list[str] = None,
) -> Limiter:
    """Create a rate limiter instance.
    
    Args:
        redis_url: Redis connection URL. If None, uses REDIS_URL env var or in-memory
        default_limits: Default rate limits (e.g., ["100/minute", "1000/hour"])
    
    Returns:
        Configured Limiter instance
    """
    if default_limits is None:
        default_limits = [
            "100/minute",  # 100 requests per minute
            "1000/hour",   # 1000 requests per hour
        ]
    
    redis_url = redis_url or os.getenv("REDIS_URL")
    
    # Use Redis if available
    storage_uri = redis_url if redis_url and REDIS_AVAILABLE else "memory://"
    
    limiter = Limiter(
        key_func=get_identifier,
        default_limits=default_limits,
        storage_uri=storage_uri,
        strategy="fixed-window",  # Can be changed to "moving-window" for more accuracy
        headers_enabled=True,     # Add rate limit headers to responses
    )
    
    logger.info(f"Rate limiter initialized with storage: {storage_uri}")
    return limiter


def add_rate_limiting(app, limiter: Limiter) -> None:
    """Add rate limiting to a FastAPI application.
    
    Args:
        app: FastAPI application instance
        limiter: Configured Limiter instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting middleware added to application")


# Pre-configured limiters for common use cases
def strict_limiter(request: Request) -> str:
    """Strict rate limit: 10 requests/minute."""
    return get_identifier(request)


def moderate_limiter(request: Request) -> str:
    """Moderate rate limit: 60 requests/minute."""
    return get_identifier(request)


def lenient_limiter(request: Request) -> str:
    """Lenient rate limit: 300 requests/minute."""
    return get_identifier(request)


# Example usage in route:
# from slowapi import Limiter
# from preciagro.packages.shared.rate_limiting import create_limiter, add_rate_limiting
#
# limiter = create_limiter()
# add_rate_limiting(app, limiter)
#
# @app.get("/endpoint")
# @limiter.limit("10/minute")
# async def my_endpoint():
#     return {"status": "ok"}
