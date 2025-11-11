"""Event dispatcher for temporal logic engine."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import and_, select

from .contracts import EngineEvent
from .dsl.compiler import TaskCompiler
from .dsl.evaluator import RuleEvaluator
from .dsl.loader import DSLLoader
from .models import ScheduledTask, TaskOutcome, async_session
from .telemetry.metrics import events_processed, tasks_created

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Main dispatcher for processing events and creating scheduled tasks."""

    def __init__(self):
        self.loader = DSLLoader()
        self.evaluator = RuleEvaluator()
        self.compiler = TaskCompiler()

    async def process_event(
        self, event: EngineEvent, context: Dict[str, Any] = None
    ) -> List[str]:
        """Process an incoming event and create scheduled tasks."""
        context = context or {}

        events_processed.labels(event_type=event.topic).inc()

        # Load all rules
        rules = self.loader.load_rules()

        created_tasks = []

        async with async_session() as session:
            for rule in rules:
                if self.evaluator.should_trigger(rule, event, context):
                    logger.info(
                        f"Rule {rule.id} triggered for event {event.id}")

                    # Compile tasks
                    tasks = self.compiler.compile_tasks(rule, event, context)

                    for task_data in tasks:
                        # Check for existing task with same dedupe key
                        if task_data.get("dedupe_key"):
                            existing_stmt = select(ScheduledTask).where(
                                ScheduledTask.dedupe_key == task_data["dedupe_key"]
                            )
                            existing = await session.execute(existing_stmt)
                            if existing.scalar():
                                logger.info(
                                    f"Skipping duplicate task: {task_data['dedupe_key']}"
                                )
                                continue

                        # Create schedule item
                        item = ScheduledTask(
                            id=task_data["id"],
                            user_id=task_data["user_id"],
                            rule_id=task_data["rule_id"],
                            schedule_time=task_data["schedule_time"],
                            payload=task_data["payload"],
                            target=task_data["target"],
                            dedupe_key=task_data.get("dedupe_key"),
                            status="pending",
                        )

                        session.add(item)
                        created_tasks.append(item.id)

                        tasks_created.labels(rule_id=rule.id).inc()

            await session.commit()

        logger.info(
            f"Created {len(created_tasks)} scheduled tasks for event {event.id}"
        )
        return created_tasks

    async def get_user_schedule(
        self, user_id: str, days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get upcoming scheduled notifications for a user."""
        async with async_session() as session:
            end_time = datetime.now(timezone.utc) + timedelta(days=days_ahead)

            stmt = (
                select(ScheduledTask)
                .where(
                    and_(
                        ScheduledTask.user_id == user_id,
                        ScheduledTask.schedule_time <= end_time,
                        ScheduledTask.status == "pending",
                    )
                )
                .order_by(ScheduledTask.schedule_time)
            )

            result = await session.execute(stmt)
            items = result.scalars().all()

            return [
                {
                    "task_id": item.id,
                    "rule_id": item.rule_id,
                    "schedule_time": item.schedule_time.isoformat(),
                    "payload": item.payload,
                    "target": item.target,
                }
                for item in items
            ]

    async def cancel_scheduled_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        async with async_session() as session:
            stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
            result = await session.execute(stmt)
            item = result.scalar()

            if item and item.status == "pending":
                item.status = "cancelled"
                await session.commit()
                return True

            return False

    async def get_task_outcomes(
        self, user_id: str = None, days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Get task completion outcomes."""
        async with async_session() as session:
            start_time = datetime.now(timezone.utc) - timedelta(days=days_back)

            stmt = select(TaskOutcome).where(
                TaskOutcome.timestamp >= start_time)

            if user_id:
                stmt = stmt.where(TaskOutcome.user_id == user_id)

            stmt = stmt.order_by(TaskOutcome.timestamp.desc())

            result = await session.execute(stmt)
            outcomes = result.scalars().all()

            return [
                {
                    "task_id": outcome.id,
                    "user_id": outcome.user_id,
                    "outcome": outcome.outcome,
                    "timestamp": outcome.timestamp.isoformat(),
                    "metadata": outcome.task_metadata,
                }
                for outcome in outcomes
            ]


# Global dispatcher instance
try:
    dispatcher = EventDispatcher()
    print(f"✓ Dispatcher created successfully: {dispatcher}")
except Exception as e:
    print(f"✗ Error creating dispatcher: {e}")
    import traceback

    traceback.print_exc()
    # Create a dummy dispatcher for now
    dispatcher = None
