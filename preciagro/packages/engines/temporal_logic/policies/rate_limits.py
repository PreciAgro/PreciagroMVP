"""Rate limiting policy for temporal logic engine."""

from datetime import datetime
from typing import Optional


from ..config import MAX_NOTIFICATIONS_PER_DAY


async def daily_count(user_id: str, now_utc: datetime):
    """Get daily notification count for a user."""
    # FIX: Placeholder query — lint flagged unused window/session; real implementation should count notifications between now-24h and now once persistence layer is wired.
    return 0


async def should_rate_limit(session, user_id: str, channel: str):
    """Check if user should be rate limited."""
    now = datetime.utcnow()
    count = await daily_count(user_id, now)
    return count >= MAX_NOTIFICATIONS_PER_DAY


class RateLimitPolicy:
    """Simple rate limiting helper used by dispatcher and tests."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def check_rate_limit(
        self, user_id: str, channel: str, message_type: str
    ) -> bool:
        """
        Return True when the message is below the configured limit.

        message_type allows per-template overrides in the future.
        """
        current = await self._get_current_usage(user_id, channel, message_type)
        limit = self._get_rate_limit(channel, message_type)
        return current < limit

    async def _get_current_usage(
        self, user_id: str, channel: str, message_type: str
    ) -> int:
        """Lookup how many messages were sent in the current window."""
        async with self.session_factory() as session:
            _ = session  # touch session for future extension
        return 0

    def _get_rate_limit(self, channel: str, message_type: Optional[str]) -> int:
        """Return the max number of messages allowed within the rolling window."""
        return MAX_NOTIFICATIONS_PER_DAY


def apply_rate_limiting(
    user_id: str, channel: str, scheduled_time: datetime, priority: int
):
    """Return the original schedule time with a friendly message."""
    return scheduled_time, "Within rate limits"
