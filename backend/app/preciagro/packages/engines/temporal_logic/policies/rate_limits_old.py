"""Rate limiting policies implementation."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


class RateLimitBucket:
    """Individual rate limit bucket for tracking usage."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.usage_count = 0
        self.window_start = datetime.utcnow()
        self.window_end = self.window_start + timedelta(seconds=window_seconds)

    def is_allowed(self, current_time: Optional[datetime] = None) -> bool:
        """Check if request is allowed within rate limit."""
        if current_time is None:
            current_time = datetime.utcnow()

        # Reset window if expired
        if current_time >= self.window_end:
            self._reset_window(current_time)

        return self.usage_count < self.limit

    def consume(self, current_time: Optional[datetime] = None) -> bool:
        """Consume a token from the bucket. Returns True if successful."""
        if current_time is None:
            current_time = datetime.utcnow()

        if self.is_allowed(current_time):
            self.usage_count += 1
            return True
        return False

    def get_reset_time(self) -> datetime:
        """Get when the rate limit window will reset."""
        return self.window_end

    def get_remaining(self) -> int:
        """Get remaining requests in current window."""
        return max(0, self.limit - self.usage_count)

    def _reset_window(self, current_time: datetime):
        """Reset the rate limit window."""
        self.usage_count = 0
        self.window_start = current_time
        self.window_end = current_time + timedelta(seconds=self.window_seconds)


class RateLimitPolicy:
    """Rate limiting policy manager."""

    def __init__(self):
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.default_limits = {
            "user_hourly": (100, 3600),  # 100 requests per hour per user
            "user_daily": (1000, 86400),  # 1000 requests per day per user
            "channel_hourly": (500, 3600),  # 500 requests per hour per channel
            "global_hourly": (10000, 3600),  # 10000 requests per hour globally
        }

        # Channel-specific limits
        self.channel_limits = {
            "whatsapp": (50, 3600),  # 50 messages per hour
            "sms": (30, 3600),  # 30 SMS per hour
            "email": (200, 3600),  # 200 emails per hour
        }

    def is_allowed(
        self,
        key: str,
        limit_type: str = "user_hourly",
        current_time: Optional[datetime] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed for given key and limit type.

        Returns:
            (allowed, info_dict)
        """
        bucket_key = f"{key}:{limit_type}"

        if bucket_key not in self.buckets:
            limit, window = self._get_limit_config(limit_type)
            self.buckets[bucket_key] = RateLimitBucket(limit, window)

        bucket = self.buckets[bucket_key]
        allowed = bucket.is_allowed(current_time)

        info = {
            "allowed": allowed,
            "limit": bucket.limit,
            "remaining": bucket.get_remaining(),
            "reset_time": bucket.get_reset_time().isoformat(),
            "window_seconds": bucket.window_seconds,
        }

        return allowed, info

    def consume(
        self,
        key: str,
        limit_type: str = "user_hourly",
        current_time: Optional[datetime] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Consume a token for given key and limit type.

        Returns:
            (consumed, info_dict)
        """
        allowed, info = self.is_allowed(key, limit_type, current_time)

        if allowed:
            bucket_key = f"{key}:{limit_type}"
            bucket = self.buckets[bucket_key]
            consumed = bucket.consume(current_time)

            # Update info
            info["consumed"] = consumed
            info["remaining"] = bucket.get_remaining()
        else:
            info["consumed"] = False

        return info["consumed"], info

    def check_multiple_limits(
        self, user_id: str, channel: str, current_time: Optional[datetime] = None
    ) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
        """Check multiple rate limits for a user/channel combination."""

        checks = {
            "user_hourly": f"user:{user_id}",
            "user_daily": f"user:{user_id}",
            "channel_hourly": f"channel:{channel}",
            "global_hourly": "global",
        }

        # Add channel-specific limit if exists
        if channel in self.channel_limits:
            checks[f"{channel}_limit"] = f"user:{user_id}:channel:{channel}"

        all_allowed = True
        results = {}

        for limit_name, key in checks.items():
            allowed, info = self.is_allowed(key, limit_name, current_time)
            results[limit_name] = info

            if not allowed:
                all_allowed = False

        return all_allowed, results

    def apply_rate_limits(
        self, user_id: str, channel: str, scheduled_time: datetime, priority: int = 5
    ) -> Tuple[datetime, str, Dict[str, Any]]:
        """
        Apply rate limiting and potentially delay message.

        Returns:
            (adjusted_time, reason, limit_info)
        """
        # High priority messages bypass some rate limits
        if priority >= 9:
            return scheduled_time, "High priority bypass", {}

        current_time = datetime.utcnow()
        allowed, limit_info = self.check_multiple_limits(user_id, channel, current_time)

        if allowed:
            # Consume tokens for all applicable limits
            self._consume_multiple_limits(user_id, channel, current_time)
            return scheduled_time, "Within rate limits", limit_info

        # Find the most restrictive limit
        earliest_reset = None
        blocking_limit = None

        for limit_name, info in limit_info.items():
            if not info["allowed"]:
                reset_time = datetime.fromisoformat(info["reset_time"])
                if earliest_reset is None or reset_time < earliest_reset:
                    earliest_reset = reset_time
                    blocking_limit = limit_name

        if earliest_reset and earliest_reset > scheduled_time:
            delay_seconds = int((earliest_reset - scheduled_time).total_seconds())
            reason = f"Rate limited by {blocking_limit}, delayed {delay_seconds}s"
            logger.info(f"Message for user {user_id} delayed due to rate limit: {reason}")
            return earliest_reset, reason, limit_info

        return scheduled_time, "Rate limit check passed", limit_info

    def _consume_multiple_limits(self, user_id: str, channel: str, current_time: datetime):
        """Consume tokens for multiple applicable limits."""
        limits_to_consume = [
            (f"user:{user_id}", "user_hourly"),
            (f"user:{user_id}", "user_daily"),
            (f"channel:{channel}", "channel_hourly"),
            ("global", "global_hourly"),
        ]

        # Add channel-specific limit
        if channel in self.channel_limits:
            limits_to_consume.append((f"user:{user_id}:channel:{channel}", f"{channel}_limit"))

        for key, limit_type in limits_to_consume:
            self.consume(key, limit_type, current_time)

    def _get_limit_config(self, limit_type: str) -> Tuple[int, int]:
        """Get limit configuration for given limit type."""

        # Check channel-specific limits
        for channel, (limit, window) in self.channel_limits.items():
            if limit_type == f"{channel}_limit":
                return limit, window

        # Check default limits
        if limit_type in self.default_limits:
            return self.default_limits[limit_type]

        # Fallback to default
        logger.warning(f"Unknown limit type: {limit_type}, using default")
        return self.default_limits["user_hourly"]

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get rate limit status for a specific user."""
        status = {}

        user_buckets = {k: v for k, v in self.buckets.items() if k.startswith(f"user:{user_id}:")}

        for bucket_key, bucket in user_buckets.items():
            limit_type = bucket_key.split(":", 2)[-1]
            status[limit_type] = {
                "limit": bucket.limit,
                "used": bucket.usage_count,
                "remaining": bucket.get_remaining(),
                "reset_time": bucket.get_reset_time().isoformat(),
            }

        return status

    def reset_user_limits(self, user_id: str) -> int:
        """Reset all rate limits for a specific user (admin function)."""
        reset_count = 0
        keys_to_remove = []

        for bucket_key in self.buckets.keys():
            if bucket_key.startswith(f"user:{user_id}:"):
                keys_to_remove.append(bucket_key)
                reset_count += 1

        for key in keys_to_remove:
            del self.buckets[key]

        logger.info(f"Reset {reset_count} rate limit buckets for user {user_id}")
        return reset_count

    def cleanup_expired_buckets(self, current_time: Optional[datetime] = None):
        """Clean up expired rate limit buckets to free memory."""
        if current_time is None:
            current_time = datetime.utcnow()

        expired_keys = []
        cleanup_threshold = timedelta(hours=24)  # Remove buckets inactive for 24h

        for bucket_key, bucket in self.buckets.items():
            if current_time > (bucket.window_end + cleanup_threshold):
                expired_keys.append(bucket_key)

        for key in expired_keys:
            del self.buckets[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired rate limit buckets")


class AdaptiveRateLimit:
    """Adaptive rate limiting based on user behavior and system load."""

    def __init__(self, base_policy: RateLimitPolicy):
        self.base_policy = base_policy
        self.user_scores: Dict[str, float] = {}  # User reputation scores
        self.system_load_factor = 1.0

    def get_adaptive_limit(self, user_id: str, base_limit: int) -> int:
        """Get adaptive limit based on user score and system load."""
        user_score = self.user_scores.get(user_id, 1.0)

        # Good users (score > 1.0) get higher limits
        # Bad users (score < 1.0) get lower limits
        adjusted_limit = int(base_limit * user_score * self.system_load_factor)

        # Ensure minimum limit of 1
        return max(1, adjusted_limit)

    def update_user_score(self, user_id: str, behavior_score: float):
        """Update user reputation score based on behavior."""
        current_score = self.user_scores.get(user_id, 1.0)

        # Exponential moving average
        alpha = 0.1
        new_score = alpha * behavior_score + (1 - alpha) * current_score

        # Keep score in reasonable bounds
        self.user_scores[user_id] = max(0.1, min(2.0, new_score))

    def set_system_load_factor(self, load_factor: float):
        """Set system load factor (0.1 to 2.0)."""
        self.system_load_factor = max(0.1, min(2.0, load_factor))


# Global rate limit policy instance
rate_limit_policy = RateLimitPolicy()
adaptive_rate_limit = AdaptiveRateLimit(rate_limit_policy)


def apply_rate_limiting(
    user_id: str, channel: str, scheduled_time: datetime, priority: int = 5
) -> Tuple[datetime, str]:
    """
    Convenience function to apply rate limiting policy.

    Args:
        user_id: User identifier
        channel: Communication channel
        scheduled_time: Originally scheduled time
        priority: Message priority (9-10 bypass some limits)

    Returns:
        Tuple of (adjusted_time, reason)
    """
    adjusted_time, reason, _ = rate_limit_policy.apply_rate_limits(
        user_id, channel, scheduled_time, priority
    )
    return adjusted_time, reason
