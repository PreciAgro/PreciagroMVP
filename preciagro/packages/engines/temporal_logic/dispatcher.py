"""Main event dispatcher and task scheduler."""
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from .contracts import EngineEvent
from .models import ScheduleItem, async_session
from .dsl.loader import DSLLoader
from .dsl.evaluator import RuleEvaluator
from .dsl.compiler import TaskCompiler
from .telemetry.metrics import events_processed, tasks_created
import logging

logger = logging.getLogger(__name__)

class EventDispatcher:
    """Main dispatcher for processing events and creating scheduled tasks."""
    
    def __init__(self):
        self.loader = DSLLoader()
        self.evaluator = RuleEvaluator()
        self.compiler = TaskCompiler()
    
    async def process_event(self, event: EngineEvent, context: Dict[str, Any] = None) -> List[str]:
        """Process an incoming event and create scheduled tasks."""
        context = context or {}
        
        events_processed.labels(event_type=event.event_type).inc()
        
        # Load all rules
        rules = self.loader.load_rules()
        
        created_tasks = []
        
        async with async_session() as session:
            for rule in rules:
                if self.evaluator.should_trigger(rule, event, context):
                    logger.info(f"Rule {rule.id} triggered for event {event.event_id}")
                    
                    # Compile tasks
                    tasks = self.compiler.compile_tasks(rule, event, context)
                    
                    for task_data in tasks:
                        # Check for existing task with same dedupe key
                        if task_data.get("dedupe_key"):
                            existing_stmt = select(ScheduleItem).where(
                                ScheduleItem.dedupe_key == task_data["dedupe_key"]
                            )
                            existing = await session.execute(existing_stmt)
                            if existing.scalar():
                                logger.info(f"Skipping duplicate task: {task_data['dedupe_key']}")
                                continue
                        
                        # Create schedule item
                        item = ScheduleItem(
                            id=task_data["id"],
                            user_id=task_data["user_id"],
                            rule_id=task_data["rule_id"],
                            schedule_time=task_data["schedule_time"],
                            payload=task_data["payload"],
                            target=task_data["target"],
                            dedupe_key=task_data.get("dedupe_key"),
                            status="pending"
                        )
                        
                        session.add(item)
                        created_tasks.append(item.id)
                        
                        tasks_created.labels(rule_id=rule.id).inc()
            
            await session.commit()
        
        logger.info(f"Created {len(created_tasks)} scheduled tasks for event {event.event_id}")
        return created_tasks
    
    async def get_user_schedule(self, user_id: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming scheduled notifications for a user."""
        async with async_session() as session:
            end_time = datetime.now(timezone.utc) + timedelta(days=days_ahead)
            
            stmt = select(ScheduleItem).where(
                and_(
                    ScheduleItem.user_id == user_id,
                    ScheduleItem.status == "pending",
                    ScheduleItem.schedule_time <= end_time
                )
            ).order_by(ScheduleItem.schedule_time)
            
            result = await session.execute(stmt)
            items = result.scalars().all()
            
            return [
                {
                    "id": item.id,
                    "rule_id": item.rule_id,
                    "schedule_time": item.schedule_time.isoformat(),
                    "message": item.payload["short_text"],
                    "channel": item.payload["channel"]
                }
                for item in items
            ]
    
    async def cancel_scheduled_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        async with async_session() as session:
            stmt = select(ScheduleItem).where(ScheduleItem.id == task_id)
            result = await session.execute(stmt)
            item = result.scalar()
            
            if item and item.status == "pending":
                item.status = "cancelled"
                await session.commit()
                return True
            
            return False

# Global dispatcher instance
dispatcher = EventDispatcher()
