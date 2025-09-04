"""Redis cache adapter for GeoContext engine."""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from redis.asyncio import Redis
from ..contracts.v1.fco import FCOResponse
from ..config import settings


class GeoContextCache:
    """Redis-based cache for geocontext results."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or Redis.from_url(
            settings.REDIS_URL or "redis://localhost:6379",
            decode_responses=True
        )
        self.default_ttl = 3600 * 24 * 7  # 7 days
        self.key_prefix = "geocontext:"

    async def get(self, context_hash: str) -> Optional[FCOResponse]:
        """Retrieve cached FCO response."""
        try:
            key = f"{self.key_prefix}{context_hash}"
            cached_data = await self.redis.get(key)

            if cached_data:
                data = json.loads(cached_data)

                # Update hit count
                await self._increment_hit_count(context_hash)

                # Return reconstructed FCOResponse
                return FCOResponse.model_validate(data["fco_response"])

            return None

        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    async def set(
        self,
        context_hash: str,
        response: FCOResponse,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Cache FCO response."""
        try:
            key = f"{self.key_prefix}{context_hash}"

            # Prepare cache data
            cache_data = {
                "context_hash": context_hash,
                "fco_response": response.model_dump(),
                "cached_at": datetime.utcnow().isoformat(),
                "hit_count": 0
            }

            # Set with TTL
            ttl = ttl_seconds or self.default_ttl
            success = await self.redis.setex(
                key,
                ttl,
                json.dumps(cache_data, default=str)
            )

            return bool(success)

        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def exists(self, context_hash: str) -> bool:
        """Check if context hash exists in cache."""
        try:
            key = f"{self.key_prefix}{context_hash}"
            return bool(await self.redis.exists(key))
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    async def delete(self, context_hash: str) -> bool:
        """Remove cached entry."""
        try:
            key = f"{self.key_prefix}{context_hash}"
            deleted = await self.redis.delete(key)
            return deleted > 0
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            # Get all geocontext keys
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)

            stats = {
                "total_entries": len(keys),
                "cache_size_mb": 0,
                "total_hits": 0,
                "avg_hit_count": 0
            }

            if keys:
                # Sample a few entries to estimate size and hits
                sample_size = min(100, len(keys))
                sample_keys = keys[:sample_size]

                total_hits = 0
                total_size = 0

                for key in sample_keys:
                    data = await self.redis.get(key)
                    if data:
                        parsed = json.loads(data)
                        total_hits += parsed.get("hit_count", 0)
                        total_size += len(data.encode('utf-8'))

                # Extrapolate statistics
                if sample_size > 0:
                    stats["total_hits"] = int(
                        total_hits * len(keys) / sample_size)
                    stats["avg_hit_count"] = total_hits / sample_size
                    stats["cache_size_mb"] = round(
                        total_size * len(keys) / sample_size / 1024 / 1024, 2)

            return stats

        except Exception as e:
            print(f"Cache stats error: {e}")
            return {"error": str(e)}

    async def clear_expired(self) -> int:
        """Clear expired entries (Redis handles this automatically, but useful for stats)."""
        try:
            # Get all keys and check TTL
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)
            expired_count = 0

            for key in keys:
                ttl = await self.redis.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_count += 1

            return expired_count

        except Exception as e:
            print(f"Clear expired error: {e}")
            return 0

    async def _increment_hit_count(self, context_hash: str):
        """Increment hit count for cache entry."""
        try:
            key = f"{self.key_prefix}{context_hash}"
            cached_data = await self.redis.get(key)

            if cached_data:
                data = json.loads(cached_data)
                data["hit_count"] = data.get("hit_count", 0) + 1
                data["last_hit"] = datetime.utcnow().isoformat()

                # Get remaining TTL
                ttl = await self.redis.ttl(key)
                if ttl > 0:
                    await self.redis.setex(
                        key,
                        ttl,
                        json.dumps(data, default=str)
                    )
        except Exception as e:
            print(f"Hit count increment error: {e}")

    async def close(self):
        """Close Redis connection."""
        try:
            await self.redis.close()
        except Exception as e:
            print(f"Cache close error: {e}")


# Global cache instance
_cache_instance: Optional[GeoContextCache] = None


def get_cache() -> GeoContextCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = GeoContextCache()
    return _cache_instance
