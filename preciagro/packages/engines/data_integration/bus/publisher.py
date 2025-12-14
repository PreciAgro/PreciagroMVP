# bus/publisher.py
# Connect to Redis using the URL from environment variable (default: localhost)
import asyncio
import datetime
import json
import logging
import os
import uuid
from decimal import Decimal
from typing import Any

logger = logging.getLogger("preciagro.data_integration.publisher")

# Prefer redis.asyncio when available. Fall back to sync redis with threadpool
# execution to avoid blocking the event loop.
_redis_async = None
_redis_sync = None
try:
    import redis.asyncio as _redis_async_pkg

    _redis_async = _redis_async_pkg.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    logger.debug("Using redis.asyncio for publisher")
except Exception:
    try:
        import redis as _redis_sync_pkg

        _redis_sync = _redis_sync_pkg.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
        logger.debug("Using sync redis for publisher (threadpool fallback)")
    except Exception:
        _redis_sync = None
        logger.debug("No redis client available for publisher; publish will be no-op")


def _build_event(item: Any) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "ingest.normalized.created",
        "occurred_at": datetime.datetime.utcnow().isoformat(),
        "item": item.model_dump(),
    }


def _json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


async def publish_ingest_created(item: Any):
    """Publish an ingest.created event asynchronously.

    If redis.asyncio is available we use it directly. Otherwise we run the
    sync redis client in a threadpool so the event loop isn't blocked.
    If no redis client is available we log the event and return.
    """
    event = _build_event(item)
    payload = json.dumps(event, default=_json_serializer)

    if _redis_async:
        try:
            await _redis_async.xadd(
                "bus:ingest.normalized.created", {"payload": payload}
            )
            return
        except Exception:
            logger.exception(
                "redis.asyncio publish failed; falling back to sync client"
            )

    if _redis_sync:
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: _redis_sync.xadd(
                    "bus:ingest.normalized.created", {"payload": payload}
                ),
            )
            return
        except Exception:
            logger.exception("sync redis publish failed")

    # As a last resort, log the event so there is an audit trail even without Redis
    logger.info("Publish fallback (no redis): %s", payload)
