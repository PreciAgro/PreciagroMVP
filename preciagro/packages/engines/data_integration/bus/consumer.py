"""Consumer stub for Redis Stream events.

This is a minimal consumer that may be started during integration tests or demos.
It uses `redis.asyncio` when available and will NOP if Redis isn't present.
"""

import asyncio
import logging
import os

logger = logging.getLogger("preciagro.data_integration.consumer")

try:
    import redis.asyncio as _redis_async

    _redis = _redis_async.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
except Exception:
    _redis = None


async def run_consumer(
    stream_name: str = "bus:ingest.normalized.created",
    group: str = "preciagro-group",
    consumer: str = "consumer-1",
):
    if not _redis:
        logger.info("Redis not available; consumer will not run")
        return

    # Non-blocking simple consumer that uses XREAD with a short block
    last_id = "$"
    while True:
        try:
            msgs = await _redis.xread({stream_name: last_id}, block=1000, count=10)
            if msgs:
                for stream, entries in msgs:
                    for entry_id, data in entries:
                        payload = data.get(b"payload") or data.get("payload")
                        logger.info(
                            "Consumed event id=%s payload=%s", entry_id, payload
                        )
                        # advance pointer
                        last_id = entry_id
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Consumer error, retrying in 1s")
            await asyncio.sleep(1)
