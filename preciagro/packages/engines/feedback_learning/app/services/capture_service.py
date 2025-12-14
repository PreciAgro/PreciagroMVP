"""CaptureService - Receives and persists feedback from upstream engines.

This service:
- Receives feedback from UX Orchestration, Farm Inventory, etc.
- Creates immutable FeedbackEvent records
- Emits correlation IDs for tracing
- Triggers async processing pipeline
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from uuid import uuid4

from ..contracts.upstream import (
    ExplicitFeedbackInput,
    ImplicitFeedbackInput,
    OutcomeFeedbackInput,
    FeedbackType,
)
from ..models.feedback_event import FeedbackEvent
from ..models.audit_trace import FeedbackAuditTrace
from ..config import settings

logger = logging.getLogger(__name__)


class CaptureService:
    """Service for capturing feedback from upstream engines.
    
    FLE receives feedback through defined contracts only.
    This service creates immutable FeedbackEvent records.
    """
    
    def __init__(self):
        """Initialize capture service."""
        self._event_store: Dict[str, FeedbackEvent] = {}  # In-memory store for now
        self._trace_store: Dict[str, FeedbackAuditTrace] = {}
        
    async def capture_explicit_feedback(
        self,
        input_data: ExplicitFeedbackInput,
    ) -> FeedbackEvent:
        """Capture explicit feedback from UX Orchestration Engine.
        
        Args:
            input_data: Explicit feedback from user
            
        Returns:
            Immutable FeedbackEvent record
        """
        correlation_id = input_data.correlation_id or str(uuid4())
        
        logger.info(
            f"Capturing explicit feedback for recommendation {input_data.recommendation_id}",
            extra={"correlation_id": correlation_id}
        )
        
        # Create immutable feedback event
        event = FeedbackEvent(
            feedback_id=input_data.feedback_id or str(uuid4()),
            recommendation_id=input_data.recommendation_id,
            reasoning_trace_id=input_data.reasoning_trace_id,
            decision_id=input_data.decision_id,
            feedback_type=FeedbackType.EXPLICIT.value,
            source_engine=input_data.source_engine,
            region_code=input_data.region_code,
            user_id=input_data.user_id,
            user_role=input_data.user_role,
            raw_payload=input_data.model_dump(),
            rating=input_data.rating,
            feedback_category=input_data.feedback_category,
            comment=input_data.comment,
            created_at=input_data.timestamp,
            received_at=datetime.utcnow(),
            correlation_id=correlation_id,
            session_id=input_data.session_id,
            metadata=input_data.metadata,
        )
        
        # Store event
        await self._store_event(event)
        
        # Initialize audit trace
        await self._init_audit_trace(event)
        
        logger.info(
            f"Captured explicit feedback {event.feedback_id}",
            extra={"correlation_id": correlation_id, "feedback_id": event.feedback_id}
        )
        
        return event
    
    async def capture_implicit_feedback(
        self,
        input_data: ImplicitFeedbackInput,
    ) -> FeedbackEvent:
        """Capture implicit feedback from UX Orchestration Engine.
        
        Args:
            input_data: Implicit behavioral signals
            
        Returns:
            Immutable FeedbackEvent record
        """
        correlation_id = str(uuid4())
        
        logger.info(
            f"Capturing implicit feedback for recommendation {input_data.recommendation_id}",
            extra={"correlation_id": correlation_id}
        )
        
        # Create immutable feedback event
        event = FeedbackEvent(
            feedback_id=input_data.feedback_id or str(uuid4()),
            recommendation_id=input_data.recommendation_id,
            reasoning_trace_id=input_data.reasoning_trace_id,
            feedback_type=FeedbackType.IMPLICIT.value,
            source_engine=input_data.source_engine,
            region_code=input_data.region_code,
            user_id=input_data.user_id,
            user_role="farmer",  # Implicit feedback is from farmers
            raw_payload=input_data.model_dump(),
            view_duration_seconds=input_data.view_duration_seconds,
            clicked_action=input_data.clicked_action,
            dismissed=input_data.dismissed,
            created_at=input_data.timestamp,
            received_at=datetime.utcnow(),
            correlation_id=correlation_id,
            metadata=input_data.metadata,
        )
        
        # Store event
        await self._store_event(event)
        
        # Initialize audit trace
        await self._init_audit_trace(event)
        
        logger.info(
            f"Captured implicit feedback {event.feedback_id}",
            extra={"correlation_id": correlation_id, "feedback_id": event.feedback_id}
        )
        
        return event
    
    async def capture_outcome_feedback(
        self,
        input_data: OutcomeFeedbackInput,
    ) -> FeedbackEvent:
        """Capture outcome feedback from Farm Inventory Engine.
        
        Args:
            input_data: Outcome evidence from action execution
            
        Returns:
            Immutable FeedbackEvent record
        """
        correlation_id = str(uuid4())
        
        logger.info(
            f"Capturing outcome feedback for recommendation {input_data.recommendation_id}",
            extra={"correlation_id": correlation_id}
        )
        
        # Create immutable feedback event
        event = FeedbackEvent(
            feedback_id=input_data.feedback_id or str(uuid4()),
            recommendation_id=input_data.recommendation_id,
            feedback_type=FeedbackType.OUTCOME.value,
            source_engine=input_data.source_engine,
            region_code=input_data.region_code,
            user_id=input_data.user_id,
            user_role="farmer",
            raw_payload=input_data.model_dump(),
            action_executed=input_data.action_executed,
            outcome_category=input_data.outcome_category,
            created_at=input_data.timestamp,
            received_at=datetime.utcnow(),
            correlation_id=correlation_id,
            metadata={
                **input_data.metadata,
                "farm_id": input_data.farm_id,
                "evidence_photo_refs": input_data.evidence_photo_refs,
                "evidence_sensor_refs": input_data.evidence_sensor_refs,
            },
        )
        
        # Store event
        await self._store_event(event)
        
        # Initialize audit trace
        await self._init_audit_trace(event)
        
        logger.info(
            f"Captured outcome feedback {event.feedback_id}",
            extra={"correlation_id": correlation_id, "feedback_id": event.feedback_id}
        )
        
        return event
    
    async def get_event(self, feedback_id: str) -> Optional[FeedbackEvent]:
        """Get feedback event by ID.
        
        Args:
            feedback_id: Feedback event ID
            
        Returns:
            FeedbackEvent if found, None otherwise
        """
        return self._event_store.get(feedback_id)
    
    async def get_events_for_recommendation(
        self,
        recommendation_id: str,
        feedback_type: Optional[str] = None,
    ) -> list[FeedbackEvent]:
        """Get all feedback events for a recommendation.
        
        Args:
            recommendation_id: Recommendation ID
            feedback_type: Optional filter by type
            
        Returns:
            List of FeedbackEvent records
        """
        events = [
            e for e in self._event_store.values()
            if e.recommendation_id == recommendation_id
        ]
        
        if feedback_type:
            events = [e for e in events if e.feedback_type == feedback_type]
        
        return sorted(events, key=lambda e: e.created_at)
    
    async def count_events(
        self,
        recommendation_id: Optional[str] = None,
        region_code: Optional[str] = None,
    ) -> int:
        """Count feedback events with optional filters.
        
        Args:
            recommendation_id: Optional recommendation filter
            region_code: Optional region filter
            
        Returns:
            Count of matching events
        """
        events = list(self._event_store.values())
        
        if recommendation_id:
            events = [e for e in events if e.recommendation_id == recommendation_id]
        if region_code:
            events = [e for e in events if e.region_code == region_code]
        
        return len(events)
    
    async def _store_event(self, event: FeedbackEvent) -> None:
        """Store feedback event (in-memory for now, will use DB).
        
        Args:
            event: FeedbackEvent to store
        """
        # Check for max feedback per recommendation
        existing_count = await self.count_events(
            recommendation_id=event.recommendation_id
        )
        if existing_count >= settings.MAX_FEEDBACK_PER_RECOMMENDATION:
            logger.warning(
                f"Max feedback reached for recommendation {event.recommendation_id}",
                extra={"feedback_id": event.feedback_id}
            )
        
        self._event_store[event.feedback_id] = event
    
    async def _init_audit_trace(self, event: FeedbackEvent) -> FeedbackAuditTrace:
        """Initialize audit trace for a feedback event.
        
        Args:
            event: FeedbackEvent to trace
            
        Returns:
            New FeedbackAuditTrace
        """
        trace = FeedbackAuditTrace(
            source_feedback_id=event.feedback_id,
            recommendation_id=event.recommendation_id,
            correlation_id=event.correlation_id,
        )
        
        # Add received step
        trace.add_step(
            step_type="received",
            description=f"Received {event.feedback_type} feedback from {event.source_engine}",
            input_artifact_id=event.feedback_id,
            input_artifact_type="FeedbackEvent",
            values_after={
                "feedback_id": event.feedback_id,
                "feedback_type": event.feedback_type,
                "region_code": event.region_code,
            }
        )
        
        self._trace_store[trace.trace_id] = trace
        
        return trace
    
    def get_trace(self, feedback_id: str) -> Optional[FeedbackAuditTrace]:
        """Get audit trace for a feedback event.
        
        Args:
            feedback_id: Feedback event ID
            
        Returns:
            FeedbackAuditTrace if found
        """
        for trace in self._trace_store.values():
            if trace.source_feedback_id == feedback_id:
                return trace
        return None
