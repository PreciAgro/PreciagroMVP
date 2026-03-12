"""Feedback Routes - Inbound endpoints for receiving feedback.

These endpoints are called by:
- UX Orchestration Engine (explicit, implicit feedback)
- Farm Inventory Engine (outcome feedback)
- API Gateway (on behalf of users)

All feedback is captured immutably and queued for processing.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4

from ..contracts.upstream import (
    ExplicitFeedbackInput,
    ImplicitFeedbackInput,
    OutcomeFeedbackInput,
    FarmerProfileContext,
    RecommendationContext,
    OutcomeTimingContext,
)
from ..services.capture_service import CaptureService
from ..services.validation_service import ValidationService
from ..services.weighting_service import WeightingService
from ..services.signal_service import SignalService
from ..services.routing_service import RoutingService
from ..services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback Capture"])

# Service instances (in production, use dependency injection)
capture_service = CaptureService()
validation_service = ValidationService()
weighting_service = WeightingService()
signal_service = SignalService()
routing_service = RoutingService()
audit_service = AuditService()


class FeedbackResponse(BaseModel):
    """Standard response for feedback submission."""

    feedback_id: str
    status: str
    message: str
    correlation_id: str
    queued_for_processing: bool = True
    warnings: list[str] = Field(default_factory=list)


class ExplicitFeedbackRequest(BaseModel):
    """Request for explicit feedback submission."""

    recommendation_id: str = Field(..., description="ID of the recommendation")
    reasoning_trace_id: Optional[str] = Field(None, description="Reasoning trace ID")
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating")
    feedback_category: str = Field("other", description="Feedback category")
    comment: Optional[str] = Field(None, max_length=2000, description="User comment")
    suggested_correction: Optional[str] = Field(None, description="Suggested correction")

    # User context
    user_id: str = Field(..., description="User ID")
    user_role: str = Field(default="farmer", description="User role")
    region_code: str = Field(..., description="Region code")
    session_id: Optional[str] = Field(None, description="Session ID")


class ImplicitFeedbackRequest(BaseModel):
    """Request for implicit feedback submission."""

    recommendation_id: str = Field(..., description="ID of the recommendation")
    reasoning_trace_id: Optional[str] = Field(None, description="Reasoning trace ID")

    # Behavioral signals
    viewed: bool = Field(default=False)
    view_duration_seconds: Optional[float] = Field(None, ge=0)
    expanded_details: bool = Field(default=False)
    clicked_action: bool = Field(default=False)
    dismissed: bool = Field(default=False)
    scroll_depth: Optional[float] = Field(None, ge=0, le=1)

    # User context
    user_id: str = Field(..., description="User ID")
    region_code: str = Field(..., description="Region code")
    device_type: Optional[str] = Field(None)


class OutcomeFeedbackRequest(BaseModel):
    """Request for outcome feedback submission."""

    recommendation_id: str = Field(..., description="ID of the recommendation")
    action_id: Optional[str] = Field(None, description="Executed action ID")

    # Outcome data
    action_executed: bool = Field(..., description="Whether action was executed")
    execution_timestamp: Optional[datetime] = Field(None)
    outcome_observed: bool = Field(default=False)
    outcome_timestamp: Optional[datetime] = Field(None)
    outcome_category: Optional[str] = Field(None)
    outcome_description: Optional[str] = Field(None, max_length=1000)

    # Evidence
    evidence_photo_refs: list[str] = Field(default_factory=list)
    evidence_sensor_refs: list[str] = Field(default_factory=list)

    # User context
    user_id: str = Field(..., description="User ID")
    farm_id: str = Field(..., description="Farm ID")
    region_code: str = Field(..., description="Region code")


async def process_feedback_pipeline(
    feedback_id: str,
    farmer_profile: Optional[dict] = None,
    recommendation_context: Optional[dict] = None,
    timing_context: Optional[dict] = None,
):
    """Background task to process feedback through the full pipeline.

    Args:
        feedback_id: ID of the feedback to process
        farmer_profile: Optional farmer profile data
        recommendation_context: Optional recommendation context
        timing_context: Optional timing context
    """
    try:
        # Get the event
        event = await capture_service.get_event(feedback_id)
        if not event:
            logger.error(f"Feedback {feedback_id} not found for processing")
            return

        # Create audit trace
        trace = await audit_service.create_trace(event)

        # Get existing events for recommendation
        existing = await capture_service.get_events_for_recommendation(event.recommendation_id)

        # Parse optional contexts
        farmer_ctx = None
        if farmer_profile:
            farmer_ctx = FarmerProfileContext(**farmer_profile)

        rec_ctx = None
        if recommendation_context:
            rec_ctx = RecommendationContext(**recommendation_context)

        timing_ctx = None
        if timing_context:
            timing_ctx = OutcomeTimingContext(**timing_context)

        # Validate
        validation_result = await validation_service.validate(event, existing, farmer_ctx)

        await audit_service.add_validation_step(
            trace.trace_id,
            validation_result.is_valid,
            {
                "is_duplicate": validation_result.is_duplicate,
                "is_contradiction": validation_result.is_contradiction,
                "is_noise": validation_result.is_noise,
                "errors": validation_result.errors,
            },
        )

        if not validation_result.is_valid:
            await audit_service.complete_trace(
                trace.trace_id, status="error", error_message="Validation failed"
            )
            return

        # Weight
        weighted = await weighting_service.compute_weight(
            event=event,
            farmer_profile=farmer_ctx,
            recommendation_context=rec_ctx,
            timing_context=timing_ctx,
            validation_flags={
                "is_duplicate": validation_result.is_duplicate,
                "is_contradiction": validation_result.is_contradiction,
                "is_noise": validation_result.is_noise,
                "duplicate_of_id": validation_result.duplicate_of_id,
                "contradiction_ids": validation_result.contradiction_ids,
                "noise_reason": validation_result.noise_reason,
            },
        )

        await audit_service.add_weighting_step(trace.trace_id, weighted)

        # Generate signal
        signal = await signal_service.generate_signal(
            weighted,
            recommendation_context=rec_ctx,
            target_engine="all",
        )

        await audit_service.add_signal_step(trace.trace_id, signal)

        # Route signal
        result = await routing_service.route_signal(signal)

        await audit_service.add_routing_step(
            trace.trace_id,
            signal.signal_id,
            result.stream,
            result.success,
            result.errors[0] if result.errors else None,
        )

        # Mark signal as routed
        if result.success:
            await signal_service.mark_routed([signal.signal_id], result.stream)

        # Complete trace
        await audit_service.complete_trace(
            trace.trace_id, status="flagged" if weighted.is_flagged else "completed"
        )

        logger.info(
            f"Processed feedback {feedback_id} successfully", extra={"signal_id": signal.signal_id}
        )

    except Exception as e:
        logger.error(f"Failed to process feedback {feedback_id}: {e}")


@router.post("/explicit", response_model=FeedbackResponse)
async def submit_explicit_feedback(
    request: ExplicitFeedbackRequest,
    background_tasks: BackgroundTasks,
):
    """Submit explicit user feedback.

    Called by UX Orchestration Engine when user rates or comments
    on a recommendation.
    """
    correlation_id = str(uuid4())

    try:
        # Convert to contract
        input_data = ExplicitFeedbackInput(
            recommendation_id=request.recommendation_id,
            reasoning_trace_id=request.reasoning_trace_id,
            rating=request.rating,
            feedback_category=request.feedback_category,
            comment=request.comment,
            suggested_correction=request.suggested_correction,
            user_id=request.user_id,
            user_role=request.user_role,
            region_code=request.region_code,
            session_id=request.session_id,
            correlation_id=correlation_id,
        )

        # Capture feedback
        event = await capture_service.capture_explicit_feedback(input_data)

        # Queue for processing
        background_tasks.add_task(
            process_feedback_pipeline,
            event.feedback_id,
        )

        return FeedbackResponse(
            feedback_id=event.feedback_id,
            status="accepted",
            message="Feedback captured and queued for processing",
            correlation_id=correlation_id,
            queued_for_processing=True,
        )

    except Exception as e:
        logger.error(f"Failed to capture explicit feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to capture feedback: {str(e)}")


@router.post("/implicit", response_model=FeedbackResponse)
async def submit_implicit_feedback(
    request: ImplicitFeedbackRequest,
    background_tasks: BackgroundTasks,
):
    """Submit implicit behavioral feedback.

    Called by UX Orchestration Engine with user interaction signals.
    """
    correlation_id = str(uuid4())

    try:
        # Convert to contract
        input_data = ImplicitFeedbackInput(
            recommendation_id=request.recommendation_id,
            reasoning_trace_id=request.reasoning_trace_id,
            viewed=request.viewed,
            view_duration_seconds=request.view_duration_seconds,
            expanded_details=request.expanded_details,
            clicked_action=request.clicked_action,
            dismissed=request.dismissed,
            scroll_depth=request.scroll_depth,
            user_id=request.user_id,
            region_code=request.region_code,
            device_type=request.device_type,
        )

        # Capture feedback
        event = await capture_service.capture_implicit_feedback(input_data)

        # Queue for processing
        background_tasks.add_task(
            process_feedback_pipeline,
            event.feedback_id,
        )

        return FeedbackResponse(
            feedback_id=event.feedback_id,
            status="accepted",
            message="Implicit feedback captured",
            correlation_id=correlation_id,
            queued_for_processing=True,
        )

    except Exception as e:
        logger.error(f"Failed to capture implicit feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to capture feedback: {str(e)}")


@router.post("/outcome", response_model=FeedbackResponse)
async def submit_outcome_feedback(
    request: OutcomeFeedbackRequest,
    background_tasks: BackgroundTasks,
):
    """Submit outcome feedback.

    Called by Farm Inventory Engine with action execution evidence.
    """
    correlation_id = str(uuid4())

    try:
        # Convert to contract
        input_data = OutcomeFeedbackInput(
            recommendation_id=request.recommendation_id,
            action_id=request.action_id,
            action_executed=request.action_executed,
            execution_timestamp=request.execution_timestamp,
            outcome_observed=request.outcome_observed,
            outcome_timestamp=request.outcome_timestamp,
            outcome_category=request.outcome_category,
            outcome_description=request.outcome_description,
            evidence_photo_refs=request.evidence_photo_refs,
            evidence_sensor_refs=request.evidence_sensor_refs,
            user_id=request.user_id,
            farm_id=request.farm_id,
            region_code=request.region_code,
        )

        # Capture feedback
        event = await capture_service.capture_outcome_feedback(input_data)

        # Queue for processing
        background_tasks.add_task(
            process_feedback_pipeline,
            event.feedback_id,
        )

        return FeedbackResponse(
            feedback_id=event.feedback_id,
            status="accepted",
            message="Outcome feedback captured",
            correlation_id=correlation_id,
            queued_for_processing=True,
        )

    except Exception as e:
        logger.error(f"Failed to capture outcome feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to capture feedback: {str(e)}")


@router.get("/count")
async def get_feedback_count(
    recommendation_id: Optional[str] = None,
    region_code: Optional[str] = None,
):
    """Get count of feedback events."""
    count = await capture_service.count_events(
        recommendation_id=recommendation_id,
        region_code=region_code,
    )
    return {"count": count}
