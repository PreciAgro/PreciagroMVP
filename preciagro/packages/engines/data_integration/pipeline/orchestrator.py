# pipeline/orchestrator.py
"""Orchestrator for Data Integration Engine.

This module exposes a small, generic orchestration layer that:
- fetches raw data from connectors
- normalizes into `NormalizedItem` using schema normalizers
- performs de-duplicated upsert into storage
- publishes an event for downstream engines
- optionally caches recent normalized items (Redis preferred, falls back to in-memory)

It deliberately keeps integration points small so other engines can consume the
published events without this file needing to depend on them.
"""

from typing import Literal, Callable, Dict, Any, Optional
import logging
import os
import json
import time
import asyncio

from ..storage.db import upsert_normalized
from ..bus.publisher import publish_ingest_created
from .normalize_openweather import normalize_openweather

logger = logging.getLogger("preciagro.data_integration.orchestrator")


# --- Simple cache layer: try Redis, otherwise in-memory TTL cache ---
_redis_async = None
try:
    # Try to use redis asyncio API (redis-py v4+ exposes redis.asyncio)
    import redis.asyncio as _redis_async_pkg

    _redis_async = _redis_async_pkg.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    logger.debug("Using redis.asyncio for cache (preciagro.data_integration)")
except Exception:
    _redis_async = None
    logger.debug(
        "redis.asyncio not available, will use in-process async cache")


class _InMemoryTTLCache:
    """A tiny async-safe in-memory TTL cache used when Redis isn't available.

    It exposes async `get` and `set` to match the redis.asyncio API surface used
    by the orchestrator. This keeps the orchestration code async end-to-end.
    """

    def __init__(self):
        self.data: Dict[str, tuple[float, str]] = {}
        # protect access in async contexts
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            v = self.data.get(key)
            if not v:
                return None
            expires_at, val = v
            if time.time() > expires_at:
                del self.data[key]
                return None
            return val

    async def set(self, key: str, value: str, ttl: int):
        async with self._lock:
            self.data[key] = (time.time() + ttl, value)


_local_cache = _InMemoryTTLCache()


async def cache_get(key: str) -> Optional[str]:
    """Async cache GET: prefer Redis asyncio, otherwise in-memory async cache."""
    if _redis_async:
        try:
            val = await _redis_async.get(key)
            if isinstance(val, (bytes, bytearray)):
                return val.decode()
            return val
        except Exception:
            logger.debug(
                "redis.asyncio get failed, falling back to memory cache")
            return await _local_cache.get(key)
    return await _local_cache.get(key)


async def cache_set(key: str, value: str, ttl: int = 300):
    """Async cache SET: prefer Redis asyncio, otherwise in-memory async cache."""
    if _redis_async:
        try:
            await _redis_async.setex(key, ttl, value)
            return
        except Exception:
            logger.debug(
                "redis.asyncio set failed, falling back to memory cache")
    await _local_cache.set(key, value, ttl)


# --- Generic orchestration ---
def _make_cache_key(source_id: str, content_hash: str) -> str:
    return f"preciagro:normalized:{source_id}:{content_hash}"


async def run_job(
    connector,
    normalizer: Callable[[Dict[str, Any]], Any],
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    scope: Literal["current", "hourly", "daily"] = "hourly",
    source_id: str = "unknown.source",
    cache_ttl: int = 300,
    units: str = "metric",
):
    """Generic job runner.

    - connector: an object with `.fetch(cursor=..., lat=..., lon=..., scope=..., units=...)` that yields raw dicts
    - normalizer: callable(raw_dict, *, source_id, kind) -> NormalizedItem
    - lat/lon/scope/source_id: passed through

    The normalizer must set `content_hash` on the returned NormalizedItem so the
    orchestrator can de-duplicate and cache results.
    """

    kind = "weather.observation" if scope == "current" else "weather.forecast"
    try:
        for raw in connector.fetch(cursor=None, lat=lat, lon=lon, scope=scope, units=units):
            try:
                item = normalizer(raw, source_id=source_id, kind=kind)
            except TypeError:
                # support older normalizer signature that expects only (raw, *, source_id)
                item = normalizer(raw, source_id=source_id)

            # caching key is based on source_id + content_hash coming from normalizer
            if not getattr(item, "content_hash", None):
                logger.warning("Normalized item missing content_hash; skipping cache for item_id=%s", getattr(
                    item, "item_id", "-"))
                content_hash = None
            else:
                content_hash = item.content_hash

            if content_hash:
                cache_key = _make_cache_key(source_id, content_hash)
                cached = await cache_get(cache_key)
                if cached:
                    logger.info(
                        "Skipping upsert; cached normalized item found for %s", item.item_id)
                    continue

            # persist (de-dupe enforced by DB unique constraint)
            await upsert_normalized(item)

            # publish event for downstream engines (async-aware)
            # Call the publisher once. If it returns a coroutine or Future,
            # await it; otherwise assume it already executed synchronously.
            try:
                maybe_awaitable = publish_ingest_created(item)
                # If publisher returned a coroutine/future, await it so
                # exceptions are propagated here and can be observed.
                if asyncio.iscoroutine(maybe_awaitable) or isinstance(maybe_awaitable, asyncio.Future):
                    await maybe_awaitable
            except Exception:
                logger.exception(
                    "Failed to publish ingest event for item=%s", getattr(item, "item_id", "-"))

            # cache the serialized item to avoid reprocessing for some TTL
            if content_hash:
                try:
                    await cache_set(cache_key, json.dumps(item.model_dump()), ttl=cache_ttl)
                except Exception:
                    logger.debug("Failed to cache item %s",
                                 item.item_id, exc_info=True)

            logger.info("Ingested item %s (%s)", item.item_id, kind)

    except Exception:
        logger.exception(
            "Job failed for source=%s lat=%s lon=%s scope=%s", source_id, lat, lon, scope)


# --- Small connector/normalizer registry for convenience ---
# Add more entries here as you implement other connectors/normalizers.
REGISTRY: Dict[str, Dict[str, Any]] = {
    "openweather.onecall": {
        "normalizer": normalize_openweather,
        "description": "OpenWeather OneCall (current/hourly/daily)",
    }
}


async def run_registered_source(source_name: str, connector, **kwargs):
    """Run a registered source by name using its configured normalizer."""
    meta = REGISTRY.get(source_name)
    if not meta:
        raise KeyError(f"Source not registered: {source_name}")
    normalizer = meta["normalizer"]
    await run_job(connector, normalizer, source_id=source_name, **kwargs)
