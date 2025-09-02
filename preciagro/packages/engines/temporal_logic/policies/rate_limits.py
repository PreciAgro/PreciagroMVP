"""Rate limiting policy for temporal logic engine."""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from ..models import async_session
from ..config import MAX_NOTIFICATIONS_PER_DAY


async def daily_count(user_id: str, now_utc: datetime):
    """Get daily notification count for a user."""
    start = now_utc - timedelta(hours=24)
    async with async_session() as session:
        # Simplified query - would need to join with actual notification tables
        return 0  # Placeholder


async def should_rate_limit(session, user_id: str, channel: str):
    """Check if user should be rate limited."""
    now = datetime.utcnow()
    count = await daily_count(user_id, now)
    return count >= MAX_NOTIFICATIONS_PER_DAY
