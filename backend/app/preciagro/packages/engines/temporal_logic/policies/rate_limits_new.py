"""Rate limiting policy for temporal logic engine."""

from datetime import datetime, timedelta

from sqlalchemy import func, select

from ..models import JobStatus, NotificationJob, Session


async def daily_count(farm_id: str, now_utc: datetime):
    """Get daily notification count for a farm."""
    start = now_utc - timedelta(hours=24)
    async with Session() as s:
        q = await s.execute(
            select(func.count(NotificationJob.id))
            .join_from(NotificationJob, NotificationJob.schedule)
            .where(
                NotificationJob.created_at >= start,
                NotificationJob.status.in_([JobStatus.sent, JobStatus.sending]),
            )
        )
        return q.scalar_one()
