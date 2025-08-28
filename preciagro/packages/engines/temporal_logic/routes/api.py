"""FastAPI routes for temporal logic engine."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from ..contracts import EngineEvent, TaskOutcomePost 
from ..models import TaskOutcome, async_session
from ..dispatcher import dispatcher
from ..security.auth import svc_auth
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/temporal", dependencies=[Depends(svc_auth)])

@router.post("/events")
async def ingest_event(event: EngineEvent, context: Dict[str, Any] = None):
    """Ingest a new event and create scheduled tasks."""
    try:
        task_ids = await dispatcher.process_event(event, context)
        return {
            "event_id": event.event_id,
            "tasks_created": len(task_ids),
            "task_ids": task_ids
        }
    except Exception as e:
        logger.error(f"Failed to process event {event.event_id}: {e}")
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
            metadata=outcome.metadata or {}
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
        raise HTTPException(status_code=404, detail="Task not found or not cancellable")

@router.get("/intents")
async def get_user_intents():
    """Get user intents (placeholder for future voice/AI integration)."""
    return {
        "intents": [
            {"id": "spray_reminder", "text": "Remind me to spray tomatoes"},
            {"id": "irrigation_reminder", "text": "Remind me to water crops in the morning"}
        ]
    }

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for temporal engine."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
