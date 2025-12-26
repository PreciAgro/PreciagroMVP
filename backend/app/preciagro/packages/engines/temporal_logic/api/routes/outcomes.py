"""API routes for task outcomes endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.security import HTTPBearer
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...contracts import OutcomeCreate, OutcomeResponse, PaginatedResponse
from ...models import ScheduledTask, TaskOutcome
from ...security.auth_old import Permission, security_middleware
from ...telemetry.metrics import engine_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/outcomes", tags=["outcomes"])
security = HTTPBearer()


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    # This should be implemented based on your database setup
    # For now, it's a placeholder
    pass


async def authenticate_user(token: str = Depends(security)) -> Dict[str, Any]:
    """Authenticate user from bearer token."""
    return security_middleware.authenticate_token(token.credentials)


@router.post("/tasks/{task_id}/outcome", response_model=OutcomeResponse)
async def record_task_outcome(
    task_id: int = Path(..., description="Task ID"),
    outcome_data: OutcomeCreate = ...,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user),
):
    """Record an outcome for a specific task."""
    try:
        # Check permissions
        security_middleware.authorize_request(current_user["user_id"], Permission.UPDATE_TASKS)

        # Validate task exists
        task_stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        task_result = await db.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Create outcome
        outcome = TaskOutcome(
            task_id=task_id,
            outcome_type=outcome_data.outcome_type,
            outcome_data=outcome_data.outcome_data,
            source=outcome_data.source,
        )

        db.add(outcome)
        await db.commit()
        await db.refresh(outcome)

        logger.info(f"Recorded outcome for task {task_id}: {outcome_data.outcome_type}")

        return OutcomeResponse(
            id=outcome.id,
            task_id=outcome.task_id,
            outcome_type=outcome.outcome_type,
            outcome_data=outcome.outcome_data,
            recorded_at=outcome.recorded_at,
            source=outcome.source,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording outcome for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/outcomes", response_model=List[OutcomeResponse])
async def get_task_outcomes(
    task_id: int = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user),
):
    """Get all outcomes for a specific task."""
    try:
        # Check permissions
        security_middleware.authorize_request(current_user["user_id"], Permission.READ_TASKS)

        # Validate task exists
        task_stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        task_result = await db.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get outcomes
        stmt = (
            select(TaskOutcome)
            .where(TaskOutcome.task_id == task_id)
            .order_by(desc(TaskOutcome.recorded_at))
        )

        result = await db.execute(stmt)
        outcomes = result.scalars().all()

        return [
            OutcomeResponse(
                id=outcome.id,
                task_id=outcome.task_id,
                outcome_type=outcome.outcome_type,
                outcome_data=outcome.outcome_data,
                recorded_at=outcome.recorded_at,
                source=outcome.source,
            )
            for outcome in outcomes
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting outcomes for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse)
async def get_outcomes(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    outcome_type: Optional[str] = Query(None, description="Filter by outcome type"),
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    source: Optional[str] = Query(None, description="Filter by source"),
    recorded_after: Optional[datetime] = Query(
        None, description="Filter outcomes recorded after this date"
    ),
    recorded_before: Optional[datetime] = Query(
        None, description="Filter outcomes recorded before this date"
    ),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user),
):
    """Get paginated list of task outcomes with optional filtering."""
    try:
        # Check permissions
        security_middleware.authorize_request(current_user["user_id"], Permission.READ_TASKS)

        # Build query
        query = select(TaskOutcome)
        conditions = []

        if outcome_type:
            conditions.append(TaskOutcome.outcome_type == outcome_type)

        if task_id:
            conditions.append(TaskOutcome.task_id == task_id)

        if source:
            conditions.append(TaskOutcome.source == source)

        if recorded_after:
            conditions.append(TaskOutcome.recorded_at >= recorded_after)

        if recorded_before:
            conditions.append(TaskOutcome.recorded_at <= recorded_before)

        if conditions:
            query = query.where(and_(*conditions))

        # Count total
        count_query = select(TaskOutcome.id).select_from(query.alias().subquery())
        total_result = await db.execute(count_query)
        total = len(total_result.fetchall())

        # Apply pagination
        query = query.order_by(desc(TaskOutcome.recorded_at))
        query = query.offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        outcomes = result.scalars().all()

        # Convert to response objects
        outcome_responses = [
            OutcomeResponse(
                id=outcome.id,
                task_id=outcome.task_id,
                outcome_type=outcome.outcome_type,
                outcome_data=outcome.outcome_data,
                recorded_at=outcome.recorded_at,
                source=outcome.source,
            )
            for outcome in outcomes
        ]

        return PaginatedResponse(
            items=outcome_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )

    except Exception as e:
        logger.error(f"Error getting outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{outcome_id}", response_model=OutcomeResponse)
async def get_outcome(
    outcome_id: int = Path(..., description="Outcome ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user),
):
    """Get a specific outcome by ID."""
    try:
        # Check permissions
        security_middleware.authorize_request(current_user["user_id"], Permission.READ_TASKS)

        # Get outcome
        stmt = select(TaskOutcome).where(TaskOutcome.id == outcome_id)
        result = await db.execute(stmt)
        outcome = result.scalar_one_or_none()

        if not outcome:
            raise HTTPException(status_code=404, detail="Outcome not found")

        return OutcomeResponse(
            id=outcome.id,
            task_id=outcome.task_id,
            outcome_type=outcome.outcome_type,
            outcome_data=outcome.outcome_data,
            recorded_at=outcome.recorded_at,
            source=outcome.source,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting outcome {outcome_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-response")
async def record_user_response(
    task_id: int,
    response_type: str,
    response_data: Dict[str, Any],
    user_id: str,
    channel: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user),
):
    """Record a user response to a message/task."""
    try:
        # Check permissions - allow users to record their own responses
        if current_user["user_id"] != user_id:
            security_middleware.authorize_request(current_user["user_id"], Permission.UPDATE_TASKS)

        # Validate task exists
        task_stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        task_result = await db.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Create outcome for user response
        outcome = TaskOutcome(
            task_id=task_id,
            outcome_type="user_response",
            outcome_data={
                "response_type": response_type,
                "response_data": response_data,
                "user_id": user_id,
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat(),
            },
            source=f"user_response_{channel}",
        )

        db.add(outcome)
        await db.commit()
        await db.refresh(outcome)

        # Record metrics
        engine_metrics.message_delivery_status(channel, "responded")

        logger.info(f"Recorded user response for task {task_id} from user {user_id}")

        return {
            "outcome_id": outcome.id,
            "task_id": task_id,
            "user_id": user_id,
            "response_type": response_type,
            "recorded_at": outcome.recorded_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording user response for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_outcomes_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user),
):
    """Get summary statistics of task outcomes."""
    try:
        # Check permissions
        security_middleware.authorize_request(current_user["user_id"], Permission.READ_TASKS)

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get outcomes from the last N days
        stmt = select(TaskOutcome).where(TaskOutcome.recorded_at >= start_date)

        result = await db.execute(stmt)
        outcomes = result.scalars().all()

        # Aggregate statistics
        outcome_type_counts = {}
        source_counts = {}
        daily_counts = {}

        for outcome in outcomes:
            # Outcome type counts
            if outcome.outcome_type not in outcome_type_counts:
                outcome_type_counts[outcome.outcome_type] = 0
            outcome_type_counts[outcome.outcome_type] += 1

            # Source counts
            if outcome.source not in source_counts:
                source_counts[outcome.source] = 0
            source_counts[outcome.source] += 1

            # Daily counts
            day_key = outcome.recorded_at.date().isoformat()
            if day_key not in daily_counts:
                daily_counts[day_key] = 0
            daily_counts[day_key] += 1

        # Calculate response rates
        user_responses = [o for o in outcomes if o.outcome_type == "user_response"]
        total_messages = len([o for o in outcomes if "message" in o.source.lower()])
        response_rate = len(user_responses) / total_messages if total_messages > 0 else 0

        return {
            "period_days": days,
            "total_outcomes": len(outcomes),
            "outcome_types": outcome_type_counts,
            "sources": source_counts,
            "daily_counts": daily_counts,
            "user_response_rate": response_rate,
            "user_responses": len(user_responses),
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting outcomes summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/conversation")
async def get_task_conversation(
    task_id: int = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user),
):
    """Get the conversation thread for a specific task (task + outcomes)."""
    try:
        # Check permissions
        security_middleware.authorize_request(current_user["user_id"], Permission.READ_TASKS)

        # Get task
        task_stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        task_result = await db.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get outcomes
        outcomes_stmt = (
            select(TaskOutcome)
            .where(TaskOutcome.task_id == task_id)
            .order_by(TaskOutcome.recorded_at)
        )

        outcomes_result = await db.execute(outcomes_stmt)
        outcomes = outcomes_result.scalars().all()

        # Build conversation thread
        conversation = []

        # Add initial task/message
        conversation.append(
            {
                "type": "task",
                "timestamp": task.created_at.isoformat(),
                "content": {
                    "task_type": task.task_type,
                    "task_config": task.task_config,
                    "status": task.status,
                },
            }
        )

        # Add execution event if executed
        if task.executed_at:
            conversation.append(
                {
                    "type": "execution",
                    "timestamp": task.executed_at.isoformat(),
                    "content": {"status": "executed", "attempt": task.attempts},
                }
            )

        # Add outcomes
        for outcome in outcomes:
            conversation.append(
                {
                    "type": "outcome",
                    "timestamp": outcome.recorded_at.isoformat(),
                    "content": {
                        "outcome_type": outcome.outcome_type,
                        "outcome_data": outcome.outcome_data,
                        "source": outcome.source,
                    },
                }
            )

        return {
            "task_id": task_id,
            "conversation": conversation,
            "task_summary": {
                "created_at": task.created_at.isoformat(),
                "status": task.status,
                "attempts": task.attempts,
                "outcomes_count": len(outcomes),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task conversation {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
