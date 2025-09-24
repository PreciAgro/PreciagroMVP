"""API routes for schedules/tasks endpoints."""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, update
from ..models import ScheduledTask, TemporalRule, TaskStatus
from ..contracts import (
    ScheduledTaskResponse, ScheduledTaskCreate, ScheduledTaskUpdate,
    PaginatedResponse, BulkOperationResponse
)
from ..security.auth import security_middleware, Permission
from ..telemetry.metrics import engine_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedules", tags=["schedules"])
security = HTTPBearer()


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    # This should be implemented based on your database setup
    # For now, it's a placeholder
    pass


async def authenticate_user(token: str = Depends(security)) -> Dict[str, Any]:
    """Authenticate user from bearer token."""
    return security_middleware.authenticate_token(token.credentials)


@router.get("/", response_model=PaginatedResponse)
async def get_scheduled_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    rule_id: Optional[int] = Query(None, description="Filter by rule ID"),
    scheduled_after: Optional[datetime] = Query(
        None, description="Filter tasks scheduled after this date"),
    scheduled_before: Optional[datetime] = Query(
        None, description="Filter tasks scheduled before this date"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get paginated list of scheduled tasks with optional filtering."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.READ_TASKS
        )

        # Build query
        query = select(ScheduledTask)
        conditions = []

        if status:
            conditions.append(ScheduledTask.status == status)

        if task_type:
            conditions.append(ScheduledTask.task_type == task_type)

        if rule_id:
            conditions.append(ScheduledTask.rule_id == rule_id)

        if scheduled_after:
            conditions.append(ScheduledTask.scheduled_for >= scheduled_after)

        if scheduled_before:
            conditions.append(ScheduledTask.scheduled_for <= scheduled_before)

        if conditions:
            query = query.where(and_(*conditions))

        # Count total
        count_query = select(ScheduledTask.id).select_from(
            query.alias().subquery())
        total_result = await db.execute(count_query)
        total = len(total_result.fetchall())

        # Apply pagination
        query = query.order_by(desc(ScheduledTask.scheduled_for))
        query = query.offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        tasks = result.scalars().all()

        # Convert to response objects
        task_responses = [
            ScheduledTaskResponse(
                id=task.id,
                rule_id=task.rule_id,
                triggering_event_id=task.triggering_event_id,
                task_type=task.task_type,
                task_config=task.task_config,
                scheduled_for=task.scheduled_for,
                executed_at=task.executed_at,
                completed_at=task.completed_at,
                status=TaskStatus(task.status),
                attempts=task.attempts,
                max_attempts=task.max_attempts,
                error_message=task.error_message,
                result=task.result,
                created_at=task.created_at,
                updated_at=task.updated_at
            )
            for task in tasks
        ]

        return PaginatedResponse(
            items=task_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )

    except Exception as e:
        logger.error(f"Error getting scheduled tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: int = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get a specific scheduled task by ID."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.READ_TASKS
        )

        # Get task
        stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return ScheduledTaskResponse(
            id=task.id,
            rule_id=task.rule_id,
            triggering_event_id=task.triggering_event_id,
            task_type=task.task_type,
            task_config=task.task_config,
            scheduled_for=task.scheduled_for,
            executed_at=task.executed_at,
            completed_at=task.completed_at,
            status=TaskStatus(task.status),
            attempts=task.attempts,
            max_attempts=task.max_attempts,
            error_message=task.error_message,
            result=task.result,
            created_at=task.created_at,
            updated_at=task.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ScheduledTaskResponse)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Create a new scheduled task."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.CREATE_RULES  # Using CREATE_RULES as proxy for task creation
        )

        # Validate rule exists
        rule_stmt = select(TemporalRule).where(
            TemporalRule.id == task_data.rule_id)
        rule_result = await db.execute(rule_stmt)
        rule = rule_result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=400, detail="Rule not found")

        # Create task
        task = ScheduledTask(
            rule_id=task_data.rule_id,
            triggering_event_id=task_data.triggering_event_id,
            task_type=task_data.task_type,
            task_config=task_data.task_config.dict(),
            scheduled_for=task_data.scheduled_for,
            max_attempts=task_data.max_attempts
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        # Record metrics
        engine_metrics.task_scheduled(
            task.task_type,
            task.task_config.get("channel", "unknown"),
            int((task.scheduled_for - datetime.utcnow()).total_seconds())
        )

        logger.info(f"Created scheduled task {task.id}")

        return ScheduledTaskResponse(
            id=task.id,
            rule_id=task.rule_id,
            triggering_event_id=task.triggering_event_id,
            task_type=task.task_type,
            task_config=task.task_config,
            scheduled_for=task.scheduled_for,
            executed_at=task.executed_at,
            completed_at=task.completed_at,
            status=TaskStatus(task.status),
            attempts=task.attempts,
            max_attempts=task.max_attempts,
            error_message=task.error_message,
            result=task.result,
            created_at=task.created_at,
            updated_at=task.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scheduled task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: int = Path(..., description="Task ID"),
    task_update: ScheduledTaskUpdate = ...,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Update a scheduled task."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.UPDATE_TASKS
        )

        # Get task
        stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update fields
        update_data = task_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if field == "status" and value:
                setattr(task, field, value.value)
            else:
                setattr(task, field, value)

        task.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(task)

        logger.info(f"Updated scheduled task {task_id}")

        return ScheduledTaskResponse(
            id=task.id,
            rule_id=task.rule_id,
            triggering_event_id=task.triggering_event_id,
            task_type=task.task_type,
            task_config=task.task_config,
            scheduled_for=task.scheduled_for,
            executed_at=task.executed_at,
            completed_at=task.completed_at,
            status=TaskStatus(task.status),
            attempts=task.attempts,
            max_attempts=task.max_attempts,
            error_message=task.error_message,
            result=task.result,
            created_at=task.created_at,
            updated_at=task.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def cancel_scheduled_task(
    task_id: int = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Cancel a scheduled task."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.CANCEL_TASKS
        )

        # Get task
        stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Can only cancel pending or running tasks
        if task.status not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in status: {task.status}"
            )

        # Cancel task
        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Cancelled scheduled task {task_id}")

        return {
            "task_id": task_id,
            "status": "cancelled",
            "cancelled_at": task.completed_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_tasks_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get summary statistics of scheduled tasks."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.READ_TASKS
        )

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get tasks from the last N days
        stmt = select(ScheduledTask).where(
            ScheduledTask.created_at >= start_date
        )

        result = await db.execute(stmt)
        tasks = result.scalars().all()

        # Aggregate statistics
        status_counts = {}
        type_counts = {}
        daily_counts = {}
        success_rates = {}

        for task in tasks:
            # Status counts
            if task.status not in status_counts:
                status_counts[task.status] = 0
            status_counts[task.status] += 1

            # Type counts
            if task.task_type not in type_counts:
                type_counts[task.task_type] = 0
            type_counts[task.task_type] += 1

            # Daily counts
            day_key = task.created_at.date().isoformat()
            if day_key not in daily_counts:
                daily_counts[day_key] = 0
            daily_counts[day_key] += 1

        # Calculate success rates by type
        for task_type in type_counts:
            type_tasks = [t for t in tasks if t.task_type == task_type]
            completed_tasks = [
                t for t in type_tasks if t.status == TaskStatus.COMPLETED.value]

            success_rates[task_type] = {
                "total": len(type_tasks),
                "completed": len(completed_tasks),
                "success_rate": len(completed_tasks) / len(type_tasks) if type_tasks else 0
            }

        return {
            "period_days": days,
            "total_tasks": len(tasks),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "daily_counts": daily_counts,
            "success_rates": success_rates,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting tasks summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-cancel")
async def bulk_cancel_tasks(
    task_ids: List[int],
    reason: str = "Bulk cancellation",
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Cancel multiple tasks in bulk."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.CANCEL_TASKS
        )

        if len(task_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel more than 100 tasks at once"
            )

        # Update tasks
        current_time = datetime.utcnow()

        update_stmt = update(ScheduledTask).where(
            and_(
                ScheduledTask.id.in_(task_ids),
                ScheduledTask.status.in_(
                    [TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
            )
        ).values(
            status=TaskStatus.CANCELLED.value,
            completed_at=current_time,
            updated_at=current_time,
            error_message=reason
        )

        result = await db.execute(update_stmt)
        cancelled_count = result.rowcount

        await db.commit()

        logger.info(f"Bulk cancelled {cancelled_count} tasks")

        return BulkOperationResponse(
            processed=len(task_ids),
            succeeded=cancelled_count,
            failed=len(task_ids) - cancelled_count,
            errors=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk task cancellation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due/count")
async def get_due_tasks_count(
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get count of tasks due for execution."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.READ_TASKS
        )

        current_time = datetime.utcnow()

        stmt = select(ScheduledTask).where(
            and_(
                ScheduledTask.scheduled_for <= current_time,
                ScheduledTask.status == TaskStatus.PENDING.value,
                ScheduledTask.attempts < ScheduledTask.max_attempts
            )
        )

        result = await db.execute(stmt)
        due_tasks = result.scalars().all()

        return {
            "due_tasks_count": len(due_tasks),
            "current_time": current_time.isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting due tasks count: {e}")
        raise HTTPException(status_code=500, detail=str(e))
