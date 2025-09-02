"""API routes for events endpoints."""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from ..models import TemporalEvent
from ..contracts import EventCreate, EventResponse, BulkOperationResponse, PaginatedResponse
from ..security.auth import security_middleware, Permission
from ..telemetry.metrics import engine_metrics
from ..evaluator import RuleEvaluator
from ..compiler import RuleCompiler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])
security = HTTPBearer()


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    # This should be implemented based on your database setup
    # For now, it's a placeholder
    pass


async def authenticate_user(token: str = Depends(security)) -> Dict[str, Any]:
    """Authenticate user from bearer token."""
    return security_middleware.authenticate_token(token.credentials)


@router.post("/", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Create a new temporal event."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.CREATE_EVENTS
        )

        # Create event in database
        event = TemporalEvent(
            event_type=event_data.event_type.value,
            source=event_data.source,
            payload=event_data.payload,
            metadata=event_data.metadata
        )

        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Record metrics
        engine_metrics.event_received(event.event_type, event.source)

        logger.info(f"Created event {event.id} of type {event.event_type}")

        return EventResponse(
            id=event.id,
            event_type=event.event_type,
            source=event.source,
            payload=event.payload,
            metadata=event.metadata,
            created_at=event.created_at,
            processed_at=event.processed_at
        )

    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse)
async def get_events(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    event_type: Optional[str] = Query(
        None, description="Filter by event type"),
    source: Optional[str] = Query(None, description="Filter by source"),
    start_date: Optional[datetime] = Query(
        None, description="Filter events after this date"),
    end_date: Optional[datetime] = Query(
        None, description="Filter events before this date"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get paginated list of events with optional filtering."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.READ_EVENTS
        )

        # Build query
        query = select(TemporalEvent)
        conditions = []

        if event_type:
            conditions.append(TemporalEvent.event_type == event_type)

        if source:
            conditions.append(TemporalEvent.source == source)

        if start_date:
            conditions.append(TemporalEvent.created_at >= start_date)

        if end_date:
            conditions.append(TemporalEvent.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # Count total
        count_query = select(TemporalEvent.id).select_from(
            query.alias().subquery())
        total_result = await db.execute(count_query)
        total = len(total_result.fetchall())

        # Apply pagination
        query = query.order_by(desc(TemporalEvent.created_at))
        query = query.offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        events = result.scalars().all()

        # Convert to response objects
        event_responses = [
            EventResponse(
                id=event.id,
                event_type=event.event_type,
                source=event.source,
                payload=event.payload,
                metadata=event.metadata,
                created_at=event.created_at,
                processed_at=event.processed_at
            )
            for event in events
        ]

        return PaginatedResponse(
            items=event_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )

    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int = Path(..., description="Event ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get a specific event by ID."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.READ_EVENTS
        )

        # Get event
        stmt = select(TemporalEvent).where(TemporalEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return EventResponse(
            id=event.id,
            event_type=event.event_type,
            source=event.source,
            payload=event.payload,
            metadata=event.metadata,
            created_at=event.created_at,
            processed_at=event.processed_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=BulkOperationResponse)
async def create_bulk_events(
    events_data: List[EventCreate],
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Create multiple events in a single request."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.CREATE_EVENTS
        )

        if len(events_data) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot create more than 100 events in a single request"
            )

        created_events = []
        errors = []

        for i, event_data in enumerate(events_data):
            try:
                event = TemporalEvent(
                    event_type=event_data.event_type.value,
                    source=event_data.source,
                    payload=event_data.payload,
                    metadata=event_data.metadata
                )

                db.add(event)
                created_events.append(event)

                # Record metrics
                engine_metrics.event_received(event.event_type, event.source)

            except Exception as e:
                errors.append({
                    "index": i,
                    "error": str(e),
                    "event_data": event_data.dict()
                })

        await db.commit()

        # Refresh to get IDs
        for event in created_events:
            await db.refresh(event)

        logger.info(f"Created {len(created_events)} events in bulk operation")

        return BulkOperationResponse(
            processed=len(events_data),
            succeeded=len(created_events),
            failed=len(errors),
            errors=errors
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk event creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{event_type}", response_model=EventResponse)
async def create_typed_event(
    event_type: str = Path(..., description="Event type"),
    payload: Dict[str, Any] = ...,
    source: str = "api",
    metadata: Dict[str, Any] = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Create an event with specific type (convenience endpoint)."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.CREATE_EVENTS
        )

        # Create event data
        event_data = EventCreate(
            event_type=event_type,
            source=source,
            payload=payload,
            metadata=metadata or {}
        )

        # Create event
        event = TemporalEvent(
            event_type=event_data.event_type,
            source=event_data.source,
            payload=event_data.payload,
            metadata=event_data.metadata
        )

        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Record metrics
        engine_metrics.event_received(event.event_type, event.source)

        logger.info(f"Created typed event {event.id} of type {event_type}")

        return EventResponse(
            id=event.id,
            event_type=event.event_type,
            source=event.source,
            payload=event.payload,
            metadata=event.metadata,
            created_at=event.created_at,
            processed_at=event.processed_at
        )

    except Exception as e:
        logger.error(f"Error creating typed event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types/summary")
async def get_event_types_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get summary of event types and their counts over a time period."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.READ_EVENTS
        )

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get events from the last N days
        stmt = select(TemporalEvent).where(
            TemporalEvent.created_at >= start_date
        )

        result = await db.execute(stmt)
        events = result.scalars().all()

        # Aggregate by type and source
        type_counts = {}
        source_counts = {}
        daily_counts = {}

        for event in events:
            # Type counts
            if event.event_type not in type_counts:
                type_counts[event.event_type] = 0
            type_counts[event.event_type] += 1

            # Source counts
            if event.source not in source_counts:
                source_counts[event.source] = 0
            source_counts[event.source] += 1

            # Daily counts
            day_key = event.created_at.date().isoformat()
            if day_key not in daily_counts:
                daily_counts[day_key] = 0
            daily_counts[day_key] += 1

        return {
            "period_days": days,
            "total_events": len(events),
            "event_types": type_counts,
            "sources": source_counts,
            "daily_counts": daily_counts,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting event types summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{event_id}/process")
async def process_event(
    event_id: int = Path(..., description="Event ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Manually trigger processing of a specific event."""
    try:
        # Check permissions (admin only)
        security_middleware.authorize_request(
            current_user["user_id"],
            Permission.ADMIN_SYSTEM
        )

        # Get event
        stmt = select(TemporalEvent).where(TemporalEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # TODO: Trigger rule evaluation and compilation for this event
        # This would integrate with the rule evaluator and compiler

        # Mark event as processed
        event.processed_at = datetime.utcnow()
        await db.commit()

        logger.info(f"Manually processed event {event_id}")

        return {
            "event_id": event_id,
            "processed_at": event.processed_at.isoformat(),
            "status": "processed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
