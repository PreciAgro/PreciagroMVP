"""API routes for intents endpoints."""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from ..models import UserIntent, TemporalEvent, ScheduledTask
from ..contracts import IntentCreate, IntentResponse, PaginatedResponse
from ..security.auth import security_middleware, Permission
from ..telemetry.metrics import engine_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/intents", tags=["intents"])
security = HTTPBearer()


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    # This should be implemented based on your database setup
    # For now, it's a placeholder
    pass


async def authenticate_user(token: str = Depends(security)) -> Dict[str, Any]:
    """Authenticate user from bearer token."""
    return security_middleware.authenticate_token(token.credentials)


@router.post("/", response_model=IntentResponse)
async def create_intent(
    intent_data: IntentCreate = ...,
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Create a new user intent."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"], 
            Permission.CREATE_INTENTS
        )
        
        # Create intent
        intent = UserIntent(
            user_id=intent_data.user_id,
            intent_type=intent_data.intent_type,
            intent_text=intent_data.intent_text,
            channel=intent_data.channel,
            confidence_score=intent_data.confidence_score,
            context_data=intent_data.context_data,
            processed=False
        )
        
        db.add(intent)
        await db.commit()
        await db.refresh(intent)
        
        # Record metrics
        engine_metrics.intent_created(intent_data.intent_type, intent_data.channel)
        
        logger.info(f"Created intent {intent.id} for user {intent_data.user_id}: {intent_data.intent_type}")
        
        return IntentResponse(
            id=intent.id,
            user_id=intent.user_id,
            intent_type=intent.intent_type,
            intent_text=intent.intent_text,
            channel=intent.channel,
            confidence_score=intent.confidence_score,
            context_data=intent.context_data,
            processed=intent.processed,
            recorded_at=intent.recorded_at
        )
    
    except Exception as e:
        logger.error(f"Error creating intent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse)
async def get_intents(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    intent_type: Optional[str] = Query(None, description="Filter by intent type"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    processed: Optional[bool] = Query(None, description="Filter by processing status"),
    recorded_after: Optional[datetime] = Query(None, description="Filter intents recorded after this date"),
    recorded_before: Optional[datetime] = Query(None, description="Filter intents recorded before this date"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get paginated list of user intents with optional filtering."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"], 
            Permission.READ_INTENTS
        )
        
        # Build query
        query = select(UserIntent)
        conditions = []
        
        if user_id:
            conditions.append(UserIntent.user_id == user_id)
        
        if intent_type:
            conditions.append(UserIntent.intent_type == intent_type)
        
        if channel:
            conditions.append(UserIntent.channel == channel)
        
        if processed is not None:
            conditions.append(UserIntent.processed == processed)
        
        if recorded_after:
            conditions.append(UserIntent.recorded_at >= recorded_after)
        
        if recorded_before:
            conditions.append(UserIntent.recorded_at <= recorded_before)
        
        if min_confidence is not None:
            conditions.append(UserIntent.confidence_score >= min_confidence)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Count total
        count_query = select(func.count(UserIntent.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(desc(UserIntent.recorded_at))
        query = query.offset((page - 1) * size).limit(size)
        
        result = await db.execute(query)
        intents = result.scalars().all()
        
        # Convert to response objects
        intent_responses = [
            IntentResponse(
                id=intent.id,
                user_id=intent.user_id,
                intent_type=intent.intent_type,
                intent_text=intent.intent_text,
                channel=intent.channel,
                confidence_score=intent.confidence_score,
                context_data=intent.context_data,
                processed=intent.processed,
                recorded_at=intent.recorded_at
            )
            for intent in intents
        ]
        
        return PaginatedResponse(
            items=intent_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    except Exception as e:
        logger.error(f"Error getting intents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{intent_id}", response_model=IntentResponse)
async def get_intent(
    intent_id: int = Path(..., description="Intent ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get a specific intent by ID."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"], 
            Permission.READ_INTENTS
        )
        
        # Get intent
        stmt = select(UserIntent).where(UserIntent.id == intent_id)
        result = await db.execute(stmt)
        intent = result.scalar_one_or_none()
        
        if not intent:
            raise HTTPException(status_code=404, detail="Intent not found")
        
        return IntentResponse(
            id=intent.id,
            user_id=intent.user_id,
            intent_type=intent.intent_type,
            intent_text=intent.intent_text,
            channel=intent.channel,
            confidence_score=intent.confidence_score,
            context_data=intent.context_data,
            processed=intent.processed,
            recorded_at=intent.recorded_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting intent {intent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{intent_id}/processed", response_model=IntentResponse)
async def mark_intent_processed(
    intent_id: int = Path(..., description="Intent ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Mark an intent as processed."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"], 
            Permission.UPDATE_INTENTS
        )
        
        # Get intent
        stmt = select(UserIntent).where(UserIntent.id == intent_id)
        result = await db.execute(stmt)
        intent = result.scalar_one_or_none()
        
        if not intent:
            raise HTTPException(status_code=404, detail="Intent not found")
        
        # Update processed status
        intent.processed = True
        await db.commit()
        await db.refresh(intent)
        
        logger.info(f"Marked intent {intent_id} as processed")
        
        return IntentResponse(
            id=intent.id,
            user_id=intent.user_id,
            intent_type=intent.intent_type,
            intent_text=intent.intent_text,
            channel=intent.channel,
            confidence_score=intent.confidence_score,
            context_data=intent.context_data,
            processed=intent.processed,
            recorded_at=intent.recorded_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking intent {intent_id} as processed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/process")
async def process_intents_bulk(
    intent_ids: List[int],
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Mark multiple intents as processed."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"], 
            Permission.UPDATE_INTENTS
        )
        
        # Update intents
        stmt = select(UserIntent).where(UserIntent.id.in_(intent_ids))
        result = await db.execute(stmt)
        intents = result.scalars().all()
        
        if not intents:
            raise HTTPException(status_code=404, detail="No intents found")
        
        processed_count = 0
        for intent in intents:
            if not intent.processed:
                intent.processed = True
                processed_count += 1
        
        await db.commit()
        
        logger.info(f"Bulk processed {processed_count} intents")
        
        return {
            "processed_count": processed_count,
            "total_requested": len(intent_ids),
            "already_processed": len(intent_ids) - processed_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk processing intents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[IntentResponse])
async def get_user_intents(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of intents to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get recent intents for a specific user."""
    try:
        # Check permissions - users can see their own intents
        if current_user["user_id"] != user_id:
            security_middleware.authorize_request(
                current_user["user_id"], 
                Permission.READ_INTENTS
            )
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get user intents
        stmt = select(UserIntent).where(
            and_(
                UserIntent.user_id == user_id,
                UserIntent.recorded_at >= start_date
            )
        ).order_by(desc(UserIntent.recorded_at)).limit(limit)
        
        result = await db.execute(stmt)
        intents = result.scalars().all()
        
        return [
            IntentResponse(
                id=intent.id,
                user_id=intent.user_id,
                intent_type=intent.intent_type,
                intent_text=intent.intent_text,
                channel=intent.channel,
                confidence_score=intent.confidence_score,
                context_data=intent.context_data,
                processed=intent.processed,
                recorded_at=intent.recorded_at
            )
            for intent in intents
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting intents for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nlp/parse")
async def parse_user_input(
    user_input: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Parse user input to extract intent (NLP boundary)."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"], 
            Permission.CREATE_INTENTS
        )
        
        text = user_input.get("text", "")
        user_id = user_input.get("user_id")
        channel = user_input.get("channel", "unknown")
        context = user_input.get("context", {})
        
        if not text or not user_id:
            raise HTTPException(status_code=400, detail="Text and user_id are required")
        
        # Simple rule-based intent classification
        # In a real implementation, this would use NLP/ML models
        intent_type = "unknown"
        confidence = 0.5
        
        text_lower = text.lower()
        
        # Weather intents
        if any(word in text_lower for word in ["weather", "rain", "temperature", "climate", "forecast"]):
            intent_type = "weather_query"
            confidence = 0.8
        
        # Farming intents
        elif any(word in text_lower for word in ["plant", "crop", "harvest", "seed", "farming", "irrigation"]):
            intent_type = "farming_advice"
            confidence = 0.8
        
        # Scheduling intents
        elif any(word in text_lower for word in ["remind", "schedule", "alert", "notification", "when"]):
            intent_type = "schedule_request"
            confidence = 0.7
        
        # Status intents
        elif any(word in text_lower for word in ["status", "update", "report", "progress", "how"]):
            intent_type = "status_query"
            confidence = 0.7
        
        # Help intents
        elif any(word in text_lower for word in ["help", "how to", "what is", "explain", "guide"]):
            intent_type = "help_request"
            confidence = 0.9
        
        # Settings intents
        elif any(word in text_lower for word in ["settings", "config", "change", "update", "preferences"]):
            intent_type = "settings_change"
            confidence = 0.8
        
        # Create intent record
        intent = UserIntent(
            user_id=user_id,
            intent_type=intent_type,
            intent_text=text,
            channel=channel,
            confidence_score=confidence,
            context_data={
                **context,
                "parsed_tokens": text_lower.split(),
                "original_input": user_input
            },
            processed=False
        )
        
        db.add(intent)
        await db.commit()
        await db.refresh(intent)
        
        # Record metrics
        engine_metrics.intent_created(intent_type, channel)
        
        logger.info(f"Parsed intent {intent.id}: {intent_type} (confidence: {confidence})")
        
        return {
            "intent_id": intent.id,
            "intent_type": intent_type,
            "confidence_score": confidence,
            "parsed_text": text,
            "user_id": user_id,
            "channel": channel,
            "recorded_at": intent.recorded_at.isoformat(),
            "suggested_responses": _get_suggested_responses(intent_type, context)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing user input: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_suggested_responses(intent_type: str, context: Dict[str, Any]) -> List[str]:
    """Get suggested responses based on intent type."""
    suggestions = {
        "weather_query": [
            "Would you like the current weather or a forecast?",
            "Which location are you interested in?",
            "Do you need weather alerts for your crops?"
        ],
        "farming_advice": [
            "What type of crop are you growing?",
            "What specific farming issue are you facing?",
            "Would you like planting or harvesting advice?"
        ],
        "schedule_request": [
            "What would you like to be reminded about?",
            "When should I remind you?",
            "How often should this reminder repeat?"
        ],
        "status_query": [
            "What status information do you need?",
            "Which crops or fields are you asking about?",
            "Do you want a summary or detailed report?"
        ],
        "help_request": [
            "What topic do you need help with?",
            "Are you new to the platform?",
            "Would you like a guided tutorial?"
        ],
        "settings_change": [
            "What settings would you like to change?",
            "Do you want to update notification preferences?",
            "Would you like to change your profile information?"
        ]
    }
    
    return suggestions.get(intent_type, ["I understand. How can I help you with that?"])


@router.get("/stats/summary")
async def get_intents_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(authenticate_user)
):
    """Get summary statistics of user intents."""
    try:
        # Check permissions
        security_middleware.authorize_request(
            current_user["user_id"], 
            Permission.READ_INTENTS
        )
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get intents from the last N days
        stmt = select(UserIntent).where(
            UserIntent.recorded_at >= start_date
        )
        
        result = await db.execute(stmt)
        intents = result.scalars().all()
        
        # Aggregate statistics
        intent_type_counts = {}
        channel_counts = {}
        user_counts = {}
        daily_counts = {}
        confidence_scores = []
        processed_count = 0
        
        for intent in intents:
            # Intent type counts
            if intent.intent_type not in intent_type_counts:
                intent_type_counts[intent.intent_type] = 0
            intent_type_counts[intent.intent_type] += 1
            
            # Channel counts
            if intent.channel not in channel_counts:
                channel_counts[intent.channel] = 0
            channel_counts[intent.channel] += 1
            
            # User counts
            if intent.user_id not in user_counts:
                user_counts[intent.user_id] = 0
            user_counts[intent.user_id] += 1
            
            # Daily counts
            day_key = intent.recorded_at.date().isoformat()
            if day_key not in daily_counts:
                daily_counts[day_key] = 0
            daily_counts[day_key] += 1
            
            # Confidence scores
            confidence_scores.append(intent.confidence_score)
            
            # Processed count
            if intent.processed:
                processed_count += 1
        
        # Calculate averages
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        processing_rate = processed_count / len(intents) if intents else 0
        
        return {
            "period_days": days,
            "total_intents": len(intents),
            "unique_users": len(user_counts),
            "intent_types": intent_type_counts,
            "channels": channel_counts,
            "top_users": dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "daily_counts": daily_counts,
            "average_confidence": avg_confidence,
            "processed_count": processed_count,
            "processing_rate": processing_rate,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting intents summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
