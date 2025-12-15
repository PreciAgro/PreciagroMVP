"""Admin Routes - Internal administration endpoints.

These endpoints are for:
- Human-in-the-Loop review of flagged feedback
- Audit trail access
- System administration

These are internal endpoints with no public access to learning data.
"""

import logging
from typing import Optional, Literal
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from uuid import uuid4

from ..contracts.downstream import FlaggedFeedbackOutput, FlagReason, SignalType, ReviewDecision
from ..services.weighting_service import WeightingService
from ..services.audit_service import AuditService
from ..services.capture_service import CaptureService
from ..models.audit_trace import FeedbackAuditTrace, AuditStep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administration"])

# Service instances
weighting_service = WeightingService()
audit_service = AuditService()
capture_service = CaptureService()


class FlaggedResponse(BaseModel):
    """Response for flagged feedback list."""

    flagged: list[FlaggedFeedbackOutput]
    count: int
    total: int


class ReviewRequest(BaseModel):
    """Request to submit a review decision."""

    flag_id: str = Field(..., description="Flag ID being reviewed")
    decision: Literal["accept", "reject", "modify", "escalate"] = Field(
        ..., description="Review decision"
    )
    accepted_weight: Optional[float] = Field(None, ge=0, le=1)
    modified_signal_type: Optional[str] = Field(None)
    rejection_reason: Optional[str] = Field(None)
    escalation_reason: Optional[str] = Field(None)
    reviewer_id: str = Field(..., description="Reviewer ID")
    reviewer_notes: Optional[str] = Field(None, max_length=1000)


class ReviewResponse(BaseModel):
    """Response for review submission."""

    flag_id: str
    status: str
    decision: str
    reviewed_at: datetime


class AuditTraceResponse(BaseModel):
    """Response for audit trace query."""

    trace_id: str
    source_feedback_id: str
    recommendation_id: str
    status: str
    steps: list[dict]
    weighted_feedback_id: Optional[str]
    learning_signal_ids: list[str]
    started_at: datetime
    completed_at: Optional[datetime]
    total_duration_ms: Optional[float]
    signature: Optional[str]


class EngineStatsResponse(BaseModel):
    """Response for engine statistics."""

    feedback_count: int
    weighted_count: int
    signal_count: int
    flagged_count: int
    audit_stats: dict
    routing_stats: dict


@router.get("/flagged", response_model=FlaggedResponse)
async def get_flagged_feedback(
    status: Optional[Literal["pending", "in_review", "resolved", "dismissed"]] = Query(
        None, description="Filter by review status"
    ),
    severity: Optional[Literal["low", "medium", "high", "critical"]] = Query(
        None, description="Filter by severity"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Result offset"),
):
    """Get list of flagged feedback for review.

    Used by Human-in-the-Loop review tools.
    """
    try:
        # Get all flagged weighted feedback
        all_weighted = list(weighting_service._weighted_store.values())
        flagged = [w for w in all_weighted if w.is_flagged]

        # Convert to output format
        outputs = []
        for weighted in flagged:
            # Get source feedback for summary
            event = await capture_service.get_event(weighted.source_feedback_id)

            # Determine flag reason
            flag_reason = FlagReason.LOW_WEIGHT
            if weighted.is_contradiction:
                flag_reason = FlagReason.CONTRADICTION
            elif weighted.is_noise:
                flag_reason = FlagReason.SUSPICIOUS_PATTERN
            elif weighted.is_duplicate:
                flag_reason = FlagReason.DUPLICATE

            # Determine severity
            if weighted.final_weight < 0.1:
                flag_severity = "critical"
            elif weighted.final_weight < 0.2:
                flag_severity = "high"
            elif weighted.final_weight < 0.3:
                flag_severity = "medium"
            else:
                flag_severity = "low"

            # Filter by severity if specified
            if severity and flag_severity != severity:
                continue

            output = FlaggedFeedbackOutput(
                flag_id=weighted.weighted_id,  # Use weighted ID as flag ID
                feedback_id=weighted.source_feedback_id,
                feedback_type=event.feedback_type if event else "unknown",
                recommendation_id=weighted.recommendation_id,
                flag_reason=flag_reason,
                flag_severity=flag_severity,
                flag_description=", ".join(weighted.flag_reasons),
                computed_weight=weighted.final_weight,
                weight_factors={
                    "base_confidence": weighted.base_confidence,
                    "farmer_experience_factor": weighted.farmer_experience_factor,
                    "historical_accuracy_factor": weighted.historical_accuracy_factor,
                    "model_confidence_factor": weighted.model_confidence_factor,
                    "environmental_stability_factor": weighted.environmental_stability_factor,
                },
                feedback_summary=(
                    f"Rating: {event.rating}, Category: {event.feedback_category}"
                    if event
                    else "No summary available"
                ),
                user_context={
                    "user_id": event.user_id if event else None,
                    "user_role": event.user_role if event else None,
                },
                review_priority=(
                    10
                    if flag_severity == "critical"
                    else (7 if flag_severity == "high" else (5 if flag_severity == "medium" else 3))
                ),
            )
            outputs.append(output)

        # Apply status filter if specified (would need to track review status)
        # For now, all are "pending"
        if status and status != "pending":
            outputs = []

        # Sort by priority descending
        outputs = sorted(outputs, key=lambda o: o.review_priority, reverse=True)

        # Apply pagination
        total = len(outputs)
        outputs = outputs[offset : offset + limit]

        return FlaggedResponse(
            flagged=outputs,
            count=len(outputs),
            total=total,
        )

    except Exception as e:
        logger.error(f"Failed to get flagged feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get flagged feedback: {str(e)}")


@router.post("/review", response_model=ReviewResponse)
async def submit_review(
    request: ReviewRequest,
):
    """Submit review decision for flagged feedback.

    Used by HITL reviewers to make decisions on flagged items.
    """
    try:
        # Create review decision
        decision = ReviewDecision(
            flag_id=request.flag_id,
            decision=request.decision,
            accepted_weight=request.accepted_weight,
            modified_signal_type=(
                SignalType(request.modified_signal_type) if request.modified_signal_type else None
            ),
            rejection_reason=request.rejection_reason,
            escalation_reason=request.escalation_reason,
            reviewer_id=request.reviewer_id,
            reviewer_notes=request.reviewer_notes,
        )

        # In a full implementation, this would:
        # 1. Update the weighted feedback status
        # 2. Potentially regenerate the signal with new weight
        # 3. Create audit trace entry
        # 4. Notify relevant parties

        logger.info(
            f"Review submitted for {request.flag_id}: {request.decision}",
            extra={"reviewer_id": request.reviewer_id},
        )

        return ReviewResponse(
            flag_id=request.flag_id,
            status="reviewed",
            decision=request.decision,
            reviewed_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to submit review: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit review: {str(e)}")


@router.get("/audit/{feedback_id}", response_model=AuditTraceResponse)
async def get_audit_trace(feedback_id: str):
    """Get audit trace for a feedback event.

    Required for Trust Engine audits and compliance.
    """
    try:
        trace = await audit_service.get_trace_by_feedback(feedback_id)

        if not trace:
            raise HTTPException(
                status_code=404, detail=f"Audit trace not found for feedback {feedback_id}"
            )

        # Convert steps to dicts for response
        step_dicts = [
            {
                "step_id": s.step_id,
                "step_number": s.step_number,
                "step_type": s.step_type,
                "description": s.description,
                "success": s.success,
                "started_at": s.started_at.isoformat(),
                "values_after": s.values_after,
            }
            for s in trace.steps
        ]

        return AuditTraceResponse(
            trace_id=trace.trace_id,
            source_feedback_id=trace.source_feedback_id,
            recommendation_id=trace.recommendation_id,
            status=trace.status,
            steps=step_dicts,
            weighted_feedback_id=trace.weighted_feedback_id,
            learning_signal_ids=trace.learning_signal_ids,
            started_at=trace.started_at,
            completed_at=trace.completed_at,
            total_duration_ms=trace.total_duration_ms,
            signature=trace.signature,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit trace: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit trace: {str(e)}")


@router.get("/audit/recommendation/{recommendation_id}")
async def get_audits_for_recommendation(recommendation_id: str):
    """Get all audit traces for a recommendation."""
    try:
        traces = await audit_service.get_traces_for_recommendation(recommendation_id)

        return {
            "recommendation_id": recommendation_id,
            "trace_count": len(traces),
            "traces": [
                {
                    "trace_id": t.trace_id,
                    "source_feedback_id": t.source_feedback_id,
                    "status": t.status,
                    "step_count": len(t.steps),
                    "started_at": t.started_at.isoformat(),
                }
                for t in traces
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get audit traces: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit traces: {str(e)}")


@router.get("/stats", response_model=EngineStatsResponse)
async def get_engine_stats():
    """Get overall FLE engine statistics."""
    try:
        from ..services.signal_service import SignalService
        from ..services.routing_service import RoutingService

        signal_service = SignalService()
        routing_service = RoutingService()

        # Counts
        feedback_count = await capture_service.count_events()
        weighted_count = len(weighting_service._weighted_store)
        signal_count = len(signal_service._signal_store)
        flagged_count = sum(1 for w in weighting_service._weighted_store.values() if w.is_flagged)

        # Audit stats
        audit_stats = audit_service.get_stats()

        # Routing stats
        routing_stats = routing_service.get_routing_stats()

        return EngineStatsResponse(
            feedback_count=feedback_count,
            weighted_count=weighted_count,
            signal_count=signal_count,
            flagged_count=flagged_count,
            audit_stats=audit_stats,
            routing_stats=routing_stats,
        )

    except Exception as e:
        logger.error(f"Failed to get engine stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/dead-letter")
async def get_dead_letter_messages(
    limit: int = Query(50, ge=1, le=200),
):
    """Get messages in dead letter queue."""
    from ..services.routing_service import RoutingService

    routing_service = RoutingService()

    count = await routing_service.get_dead_letter_count()
    messages = routing_service._message_store.get("dead_letter", [])[:limit]

    return {
        "count": count,
        "messages": messages,
    }
