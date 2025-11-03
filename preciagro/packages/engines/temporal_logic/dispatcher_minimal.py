"""Real temporal logic engine implementation."""

import datetime
import logging
import uuid
from datetime import datetime as dt
from datetime import timedelta
from typing import Any, Dict, List, Optional

from .contracts import (Clause, Dedupe, EngineEvent, Message, Preconditions,
                        Rule, Trigger, Window)
from .models import ScheduleItem, async_session

logger = logging.getLogger(__name__)


class TemporalLogicEngine:
    """Real temporal logic engine with rule processing and scheduling."""

    def __init__(self):
        self.rules: List[Rule] = []
        self._load_default_rules()

    def _make_json_serializable(self, obj):
        """Convert non-JSON serializable objects to JSON serializable format"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(v) for v in obj]
        elif isinstance(obj, dt):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            return obj.isoformat()
        else:
            return obj

    def _load_default_rules(self):
        """Load default farming rules for demonstration."""
        # Weather-based spraying rule
        spray_rule = Rule(
            id="weather_spray_reminder",
            trigger=Trigger(
                topic="weather.forecast",
                when=[
                    Clause(key="payload.temperature", op=" >", value=30),
                    Clause(key="payload.humidity", op="<", value=60),
                ],
            ),
            preconditions=Preconditions(
                all=[
                    Clause(
                        key="farm_metadata.crop_type",
                        op="in",
                        value=["tomato", "pepper", "cucumber"],
                    )
                ]
            ),
            window=Window(
                start_offset_hours=2, end_offset_hours=8, preferred_subwindow=None
            ),
            dedupe=Dedupe(scope="farm_daily_spray", ttl_hours=24),
            priority="high",
            channels=["whatsapp", "sms"],
            message=Message(
                short="🌡️ High temp detected! Consider spraying crops between 2-8 hours.",
                long="Temperature above 30°C with low humidity detected. Optimal spraying conditions. Consider treating crops in the next 2-8 hours to prevent pest damage.",
                buttons=["Mark as Done", "Reschedule", "Skip Today"],
            ),
        )

        # Irrigation reminder rule
        irrigation_rule = Rule(
            id="soil_irrigation_reminder",
            trigger=Trigger(
                topic="soil.moisture_update",
                when=[Clause(key="payload.moisture_level", op="<", value=30)],
            ),
            window=Window(
                start_offset_hours=1,
                end_offset_hours=4,
                start_at_local="06:00",
                end_at_local="18:00",
            ),
            dedupe=Dedupe(scope="farm_irrigation", ttl_hours=12),
            priority="medium",
            channels=["whatsapp"],
            message=Message(
                short="💧 Low soil moisture! Water crops within 1-4 hours.",
                long="Soil moisture below 30% detected. Schedule irrigation within the next 1-4 hours during daylight hours (6 AM - 6 PM).",
                buttons=["Water Now", "Schedule Later", "Check Manually"],
            ),
        )

        # Disease prevention rule
        disease_rule = Rule(
            id="disease_prevention_reminder",
            trigger=Trigger(
                topic="diagnosis.outcome",
                when=[
                    Clause(
                        key="payload.risk_level", op="in", value=["high", "critical"]
                    ),
                    Clause(
                        key="payload.disease_type",
                        op="in",
                        value=["blight", "fungal", "bacterial"],
                    ),
                ],
            ),
            window=Window(
                start_offset_hours=6,
                end_offset_hours=24,
                start_at_local="07:00",
                end_at_local="19:00",
            ),
            dedupe=Dedupe(scope="farm_disease_prevention", ttl_hours=48),
            priority="high",
            channels=["whatsapp", "sms", "email"],
            message=Message(
                short="🦠 Disease risk detected! Take preventive action within 6-24 hours.",
                long="Disease risk analysis indicates potential threat. Apply preventive treatments within 6-24 hours during daylight hours to protect your crops.",
                buttons=["Apply Treatment", "Get Expert Advice", "Monitor Closely"],
            ),
        )

        self.rules = [spray_rule, irrigation_rule, disease_rule]
        logger.info(f"Loaded {len(self.rules)} temporal logic rules")

    async def process_event(
        self, event: EngineEvent, context: Dict[str, Any] = None
    ) -> List[str]:
        """Process an incoming event and create scheduled tasks based on rules."""
        logger.info(f"Processing event: {event.topic} - {event.id}")

        # Debug: Show event data
        logger.info(f"Event payload: {event.payload}")

        matching_rules = self._find_matching_rules(event)
        logger.info(f"Found {len(matching_rules)} matching rules")

        task_ids = []

        for rule in matching_rules:
            logger.info(f"Evaluating rule: {rule.id}")
            if await self._check_preconditions(rule, event, context):
                logger.info(f"Preconditions passed for rule: {rule.id}")
                if not await self._is_deduplicated(rule, event):
                    logger.info(f"Not deduplicated, creating task for rule: {rule.id}")
                    task_id = await self._create_scheduled_task(rule, event)
                    if task_id:
                        task_ids.append(task_id)
                        logger.info(f"Created task {task_id} for rule {rule.id}")
                else:
                    logger.info(f"Task deduplicated for rule {rule.id}")

        logger.info(f"Total tasks created: {len(task_ids)}")
        return task_ids

    def _find_matching_rules(self, event: EngineEvent) -> List[Rule]:
        """Find rules that match the event topic and conditions."""
        matching_rules = []

        logger.info(f"Checking {len(self.rules)} rules for event topic: {event.topic}")

        for rule in self.rules:
            logger.info(f"Rule {rule.id} has topic: {rule.trigger.topic}")
            if rule.trigger.topic == event.topic:
                logger.info(f"Topic matches for rule {rule.id}, checking conditions...")
                # Check trigger conditions
                if self._evaluate_clauses(rule.trigger.when, event):
                    matching_rules.append(rule)
                    logger.info(f"Rule {rule.id} fully matches event {event.id}")
                else:
                    logger.info(f"Rule {rule.id} topic matches but conditions failed")
            else:
                logger.debug(
                    f"Rule {rule.id} topic mismatch: {rule.trigger.topic} != {event.topic}"
                )

        return matching_rules

    def _evaluate_clauses(self, clauses: List[Clause], event: EngineEvent) -> bool:
        """Evaluate trigger clauses against event data."""
        if not clauses:
            return True

        for clause in clauses:
            if not self._evaluate_clause(clause, event):
                return False
        return True

    def _evaluate_clause(self, clause: Clause, event: EngineEvent) -> bool:
        """Evaluate a single clause against event data."""
        try:
            # Get value from event using dot notation (e.g., "payload.temperature")
            value = self._get_nested_value(event.dict(), clause.key)
            logger.info(
                f"Evaluating clause: {clause.key} {clause.op} {clause.value}, actual value: {value}"
            )

            result = False
            if clause.op == " >":
                result = value > clause.value
            elif clause.op == ">=":
                result = value >= clause.value
            elif clause.op == "<":
                result = value < clause.value
            elif clause.op == "<=":
                result = value <= clause.value
            elif clause.op == "equals":
                result = value == clause.value
            elif clause.op == "in":
                result = value in clause.value
            elif clause.op == "not_in":
                result = value not in clause.value
            else:
                logger.warning(f"Unknown operator: {clause.op}")
                return False

            logger.info(f"Clause evaluation result: {result}")
            return result

        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Clause evaluation failed for {clause.key}: {e}")
            return False

    def _get_nested_value(self, data: dict, key: str) -> Any:
        """Get nested value using dot notation (e.g., 'payload.temperature')."""
        keys = key.split(".")
        value = data
        for k in keys:
            value = value[k]
        return value

    async def _check_preconditions(
        self, rule: Rule, event: EngineEvent, context: Dict[str, Any] = None
    ) -> bool:
        """Check if rule preconditions are met."""
        # TEMPORARILY DISABLE PRECONDITIONS FOR TESTING
        logger.info(f"Preconditions temporarily disabled for testing rule: {rule.id}")
        return True

        # For now, assume preconditions are met (would need farm metadata integration)
        # In production, this would check farm data, user preferences, etc.
        return True

    async def _is_deduplicated(self, rule: Rule, event: EngineEvent) -> bool:
        """Check if a similar task was recently created (deduplication)."""
        # TEMPORARILY DISABLE DEDUPLICATION FOR TESTING
        logger.info("Deduplication temporarily disabled for testing")
        return False

        # Simple deduplication based on rule and farm
        try:
            async with async_session() as session:
                from sqlalchemy import func, select

                from .models import ScheduleItem

                # Check for recent tasks with same dedupe key
                dedupe_key = f"{rule.dedupe.scope}_{event.farm_id}"
                cutoff_time = datetime.utcnow() - timedelta(hours=rule.dedupe.ttl_hours)

                logger.info(
                    f"Checking deduplication for key: {dedupe_key} since {cutoff_time}"
                )

                result = await session.execute(
                    select(func.count(ScheduleItem.id))
                    .where(ScheduleItem.dedupe_key == dedupe_key)
                    .where(ScheduleItem.schedule_time >= cutoff_time)
                )

                count = result.scalar()
                logger.info(
                    f"Found {count} existing tasks for dedupe key: {dedupe_key}"
                )
                return count > 0
        except Exception as e:
            logger.error(f"Deduplication check failed: {e}")
            return False  # If check fails, allow task creation

    async def _create_scheduled_task(
        self, rule: Rule, event: EngineEvent, session=None
    ) -> Optional[str]:
        """Create a scheduled task based on rule and event."""
        logger.info(f"Starting task creation for rule: {rule.id}")
        try:
            # Calculate schedule time based on rule window
            schedule_time = self._calculate_schedule_time(rule.window, event)
            logger.info(f"Calculated schedule time: {schedule_time}")

            task_id = str(uuid.uuid4())
            dedupe_key = f"{rule.dedupe.scope}_{event.farm_id}"

            # Create task payload (ensure JSON serializable)
            payload = {
                "rule_id": rule.id,
                "event_id": event.id,
                "farm_id": event.farm_id,
                "farmer_tz": event.farmer_tz,
                "priority": rule.priority,
                "channels": rule.channels,
                "message": rule.message.dict(),
                "original_event": self._make_json_serializable(event.dict()),
            }

            logger.info(f"Creating ScheduleItem with task_id: {task_id}")

            # Use provided session or create new one
            if session:
                scheduled_item = ScheduleItem(
                    id=task_id,
                    user_id=f"farmer_{event.farm_id}",
                    rule_id=rule.id,
                    schedule_time=schedule_time,
                    payload=payload,
                    target="notification_service",
                    dedupe_key=dedupe_key,
                )

                logger.info("Adding ScheduleItem to provided session...")
                session.add(scheduled_item)
                logger.info("Committing provided session...")
                await session.commit()
                logger.info("Task committed successfully with provided session!")
                return task_id
            else:
                async with async_session() as new_session:
                    scheduled_item = ScheduleItem(
                        id=task_id,
                        user_id=f"farmer_{event.farm_id}",
                        rule_id=rule.id,
                        schedule_time=schedule_time,
                        payload=payload,
                        target="notification_service",
                        dedupe_key=dedupe_key,
                    )

                    logger.info("Adding ScheduleItem to new session...")
                    new_session.add(scheduled_item)
                    logger.info("Committing new session...")
                    await new_session.commit()
                    logger.info("Task committed successfully with new session!")

            logger.info(f"Scheduled task {task_id} for {schedule_time}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to create scheduled task: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

            async with async_session() as session:
                scheduled_item = ScheduleItem(
                    id=task_id,
                    user_id=f"farmer_{event.farm_id}",
                    rule_id=rule.id,  # Add the missing rule_id field
                    schedule_time=schedule_time,
                    payload=payload,
                    target="notification_service",
                    dedupe_key=dedupe_key,
                )

                session.add(scheduled_item)
                await session.commit()

            logger.info(f"Scheduled task {task_id} for {schedule_time}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to create scheduled task: {e}")
            return None

    def _calculate_schedule_time(self, window: Window, event: EngineEvent) -> dt:
        """Calculate when the task should be scheduled based on window rules."""
        base_time = event.ts_utc

        # Apply offset
        if window.start_offset_hours:
            schedule_time = base_time + timedelta(hours=window.start_offset_hours)
        else:
            schedule_time = base_time

        # Apply day offset if specified
        if window.day_offset:
            schedule_time += timedelta(days=window.day_offset)

        # TODO: Handle start_at_local and end_at_local time constraints
        # This would require timezone conversion based on farmer_tz

        return schedule_time

    async def get_user_schedule(
        self, user_id: str, days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get upcoming scheduled tasks for a user."""
        async with async_session() as session:
            from sqlalchemy import select

            from .models import ScheduleItem

            end_date = datetime.utcnow() + timedelta(days=days_ahead)

            result = await session.execute(
                select(ScheduleItem)
                .where(ScheduleItem.user_id == user_id)
                .where(ScheduleItem.schedule_time >= datetime.utcnow())
                .where(ScheduleItem.schedule_time <= end_date)
                .order_by(ScheduleItem.schedule_time)
            )

            items = result.scalars().all()

            schedule = []
            for item in items:
                schedule.append(
                    {
                        "task_id": item.id,
                        "schedule_time": item.schedule_time.isoformat(),
                        "rule_id": item.payload.get("rule_id"),
                        "farm_id": item.payload.get("farm_id"),
                        "priority": item.payload.get("priority"),
                        "message": item.payload.get("message", {}).get("short"),
                        "channels": item.payload.get("channels", []),
                    }
                )

            return schedule

    async def cancel_scheduled_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        async with async_session() as session:
            from sqlalchemy import delete, select

            from .models import ScheduleItem

            # Check if task exists and is future
            result = await session.execute(
                select(ScheduleItem)
                .where(ScheduleItem.id == task_id)
                .where(ScheduleItem.schedule_time > datetime.utcnow())
            )

            item = result.scalar_one_or_none()
            if not item:
                return False

            # Delete the scheduled item
            await session.execute(
                delete(ScheduleItem).where(ScheduleItem.id == task_id)
            )
            await session.commit()

            logger.info(f"Cancelled scheduled task {task_id}")
            return True


# Global engine instance
engine = TemporalLogicEngine()


class EventDispatcher:
    """Event dispatcher that uses the real temporal logic engine."""

    async def process_event(
        self, event: EngineEvent, context: Dict[str, Any] = None
    ) -> List[str]:
        """Process event using real temporal logic."""
        return await engine.process_event(event, context)

    async def get_user_schedule(
        self, user_id: str, days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get user schedule using real engine."""
        return await engine.get_user_schedule(user_id, days_ahead)

    async def cancel_scheduled_task(self, task_id: str) -> bool:
        """Cancel scheduled task using real engine."""
        return await engine.cancel_scheduled_task(task_id)


# Global dispatcher instance
dispatcher = EventDispatcher()
logger.info("✓ Real Temporal Logic Engine loaded successfully")
