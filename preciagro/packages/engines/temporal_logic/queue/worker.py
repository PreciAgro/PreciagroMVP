"""ARQ worker for processing scheduled notifications."""

import logging
from datetime import datetime, timedelta, timezone

from arq.connections import RedisSettings
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..channels.twilio_sms import TwilioSMSSender
from ..channels.whatsapp_meta import WhatsAppMetaSender
from ..config import REDIS_URL
from ..models import NotificationJob, ScheduleItem, async_session
from ..policies.quiet_hours import is_quiet_hours
from ..policies.rate_limits import should_rate_limit
from ..telemetry.metrics import (notification_attempts, notification_latency,
                                 notification_results)

logger = logging.getLogger(__name__)

# Channel registry
CHANNELS = {"whatsapp": WhatsAppMetaSender(), "sms": TwilioSMSSender()}


async def process_due_notifications(ctx):
    """Process notifications that are due."""
    async with async_session() as session:
        now = datetime.now(timezone.utc)

        # Get due notifications
        stmt = select(ScheduleItem).where(
            and_(ScheduleItem.schedule_time <= now, ScheduleItem.status == "pending")
        )

        result = await session.execute(stmt)
        due_items = result.scalars().all()

        for item in due_items:
            try:
                await process_notification_item(session, item)
            except Exception as e:
                logger.error(f"Failed to process notification {item.id}: {e}")
                item.status = "failed"
                await session.commit()


async def process_notification_item(session: AsyncSession, item: ScheduleItem):
    """Process a single notification item."""
    start_time = datetime.now(timezone.utc)

    # Check quiet hours
    if is_quiet_hours(item.target.get("timezone", "UTC")):
        # Reschedule for tomorrow at 8am
        tomorrow_8am = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=8, minute=0, second=0
        )
        item.schedule_time = tomorrow_8am
        await session.commit()
        return

    # Check rate limits
    if await should_rate_limit(session, item.user_id, item.payload["channel"]):
        item.status = "rate_limited"
        await session.commit()
        return

    # Get channel
    channel_name = item.payload["channel"]
    channel = CHANNELS.get(channel_name)
    if not channel:
        logger.error(f"Unknown channel: {channel_name}")
        item.status = "failed"
        await session.commit()
        return

    # Create notification job
    job = NotificationJob(
        schedule_item_id=item.id,
        channel=channel_name,
        target=item.target,
        payload=item.payload,
        status="sending",
    )
    session.add(job)
    await session.flush()

    # Send notification
    notification_attempts.labels(channel=channel_name).inc()

    try:
        result = await channel.send(item.target, item.payload)

        job.status = "sent"
        job.result = result
        item.status = "completed"

        notification_results.labels(channel=channel_name, result="success").inc()

    except Exception as e:
        logger.error(f"Failed to send via {channel_name}: {e}")
        job.status = "failed"
        job.error = str(e)
        item.status = "failed"

        notification_results.labels(channel=channel_name, result="error").inc()

    # Record timing
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    notification_latency.labels(channel=channel_name).observe(duration)

    await session.commit()


class WorkerSettings:
    """ARQ worker settings."""

    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    functions = [process_due_notifications]
    cron_jobs = [
        # Check for due notifications every minute
        {"coroutine": process_due_notifications, "minute": "*"}
    ]
