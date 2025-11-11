"""FastAPI routes for temporal logic engine."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..contracts import EngineEvent, TaskOutcomePost
from ..dispatcher_minimal import dispatcher
from ..models import TaskOutcome, async_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/temporal")  # Temporarily disable auth for testing


@router.post("/events")
async def ingest_event(event: EngineEvent, context: Dict[str, Any] = None):
    """Ingest a new event and create scheduled tasks."""
    try:
        task_ids = await dispatcher.process_event(event, context)
        return {
            "event_id": event.id,  # Fixed: use event.id instead of event.event_id
            "tasks_created": len(task_ids),
            "task_ids": task_ids,
        }
    except Exception as e:
        logger.error(f"Failed to process event {event.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outcomes")
async def record_outcome(outcome: TaskOutcomePost):
    """Record task completion outcome."""
    async with async_session() as session:
        task_outcome = TaskOutcome(
            id=outcome.task_id,
            user_id=outcome.user_id,
            outcome=outcome.outcome,
            timestamp=outcome.timestamp or datetime.utcnow(),
            task_metadata=outcome.metadata or {},
        )

        session.add(task_outcome)
        await session.commit()

        return {"status": "recorded"}


@router.get("/schedule/{user_id}")
async def get_user_schedule(user_id: str, days_ahead: int = 7):
    """Get upcoming scheduled notifications for a user."""
    schedule = await dispatcher.get_user_schedule(user_id, days_ahead)
    return {"user_id": user_id, "schedule": schedule}


@router.delete("/schedule/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a scheduled task."""
    cancelled = await dispatcher.cancel_scheduled_task(task_id)
    if cancelled:
        return {"status": "cancelled"}
    else:
        raise HTTPException(
            status_code=404, detail="Task not found or not cancellable")


@router.get("/intents")
async def get_user_intents():
    """Get user intents (placeholder for future voice/AI integration)."""
    return {
        "intents": [
            {"id": "spray_reminder", "text": "Remind me to spray tomatoes"},
            {
                "id": "irrigation_reminder",
                "text": "Remind me to water crops in the morning",
            },
        ]
    }


# Health check endpoint


@router.get("/health")
async def health_check():
    """Health check for temporal engine."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/debug/rules")
async def debug_rules():
    """Debug endpoint to see loaded rules."""
    from ..dispatcher_minimal import engine

    rules_info = []
    for rule in engine.rules:
        rules_info.append(
            {
                "id": rule.id,
                "topic": rule.trigger.topic,
                "conditions": [
                    {"key": clause.key, "op": clause.op, "value": clause.value}
                    for clause in rule.trigger.when
                ],
                "priority": rule.priority,
                "message": rule.message.short,
            }
        )
    return {"rules_loaded": len(engine.rules), "rules": rules_info}


@router.post("/debug/test-matching")
async def debug_test_matching(event: EngineEvent):
    """Debug endpoint to test rule matching without creating tasks."""
    from ..dispatcher_minimal import engine

    matching_rules = engine._find_matching_rules(event)

    debug_info = {
        "event": {"topic": event.topic, "id": event.id, "payload": event.payload},
        "total_rules": len(engine.rules),
        "matching_rules": len(matching_rules),
        "matched_rule_ids": [rule.id for rule in matching_rules],
        "rule_evaluations": [],
    }

    # Test each rule individually
    for rule in engine.rules:
        rule_eval = {
            "rule_id": rule.id,
            "topic_match": rule.trigger.topic == event.topic,
            "conditions_result": None,
            "condition_details": [],
        }

        if rule.trigger.topic == event.topic:
            rule_eval["conditions_result"] = engine._evaluate_clauses(
                rule.trigger.when, event
            )

            # Test each condition
            for clause in rule.trigger.when:
                try:
                    value = engine._get_nested_value(event.dict(), clause.key)
                    condition_detail = {
                        "key": clause.key,
                        "op": clause.op,
                        "expected": clause.value,
                        "actual": value,
                        "result": engine._evaluate_clause(clause, event),
                    }
                except Exception as e:
                    condition_detail = {
                        "key": clause.key,
                        "op": clause.op,
                        "expected": clause.value,
                        "actual": None,
                        "result": False,
                        "error": str(e),
                    }
                rule_eval["condition_details"].append(condition_detail)

        debug_info["rule_evaluations"].append(rule_eval)

    return debug_info


@router.post("/debug/test-task-creation")
async def debug_test_task_creation():
    """Debug endpoint to test if we can create tasks in database."""
    import uuid
    from datetime import datetime

    from ..models import ScheduledTask, async_session

    try:
        async with async_session() as session:
            task_id = str(uuid.uuid4())
            test_task = ScheduledTask(
                id=task_id,
                user_id="test_user",
                rule_id="test_rule",  # Add the missing rule_id field
                schedule_time=datetime.utcnow() + timedelta(hours=2),
                payload={"test": "data"},
                target="test_target",
                dedupe_key="test_dedupe",
            )

            session.add(test_task)
            await session.commit()

            return {
                "status": "success",
                "task_id": task_id,
                "message": "Task creation works!",
            }
    except Exception as e:
        return {"status": "error", "error": str(e), "message": "Task creation failed!"}
