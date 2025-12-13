"""API Routes for Trust & Explainability Engine.

Versioned, authenticated, documented endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from ..contracts.v1.schemas import (
    ExplanationRequest,
    ExplanationResponse,
    ReasoningTrace,
    FeedbackPayload,
)
from ..services.explanation_service import ExplanationService
from ..services.trace_service import TraceService
from ..services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["trust-explainability"])

# Service instances (in production, use dependency injection)
_explanation_service: Optional[ExplanationService] = None
_trace_service: Optional[TraceService] = None
_feedback_service: Optional[FeedbackService] = None


def get_explanation_service() -> ExplanationService:
    """Get or create explanation service instance."""
    global _explanation_service
    if _explanation_service is None:
        _explanation_service = ExplanationService()
    return _explanation_service


def get_trace_service() -> TraceService:
    """Get or create trace service instance."""
    global _trace_service
    if _trace_service is None:
        _trace_service = TraceService()
    return _trace_service


def get_feedback_service() -> FeedbackService:
    """Get or create feedback service instance."""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    engine: str
    version: str
    trace_count: int


class OneLinerRequest(BaseModel):
    """Request for one-line explanation."""
    model_type: str
    model_id: str
    model_outputs: dict
    language: str = "en"


class FeedbackResponse(BaseModel):
    """Feedback submission response."""
    success: bool
    message: str
    trace_id: Optional[str] = None
    feedback_type: Optional[str] = None


@router.get("/health", response_model=HealthResponse)
async def health_check(
    trace_service: TraceService = Depends(get_trace_service)
) -> HealthResponse:
    """Health check endpoint.
    
    Returns engine status and basic stats.
    """
    return HealthResponse(
        status="healthy",
        engine="trust_explainability",
        version="1.0.0",
        trace_count=trace_service.get_trace_count()
    )


@router.post("/explain", response_model=ExplanationResponse)
async def explain(
    request: ExplanationRequest,
    service: ExplanationService = Depends(get_explanation_service)
) -> ExplanationResponse:
    """Generate explanation for a model output.
    
    This is the main endpoint for the Trust & Explainability Engine.
    It generates tiered explanations (farmer, expert, auditor),
    computes confidence metrics, and runs safety validation.
    
    Args:
        request: Explanation request with model outputs and context
        
    Returns:
        ExplanationResponse with tiered explanations and metadata
    """
    logger.info(f"Received explanation request: {request.request_id}")
    
    response = await service.explain(request)
    
    logger.info(
        f"Explanation generated for {request.request_id}: "
        f"confidence={response.confidence:.2f}, safety={response.safety_status}"
    )
    
    return response


@router.post("/explain/fast", response_model=dict)
async def explain_fast(
    request: OneLinerRequest,
    service: ExplanationService = Depends(get_explanation_service)
) -> dict:
    """Generate quick one-line explanation.
    
    Faster endpoint for simple explanations without full trace.
    
    Args:
        request: One-liner request
        
    Returns:
        Dictionary with one-line explanation
    """
    # Convert to full request
    full_request = ExplanationRequest(
        model_type=request.model_type,
        model_id=request.model_id,
        model_outputs=request.model_outputs,
        language=request.language,
        include_safety_check=False,
        include_confidence=False
    )
    
    explanation = await service.explain_fast(full_request)
    
    return {"explanation": explanation}


@router.get("/trace/{trace_id}", response_model=ReasoningTrace)
async def get_trace(
    trace_id: str,
    service: TraceService = Depends(get_trace_service)
) -> ReasoningTrace:
    """Retrieve a reasoning trace by ID.
    
    Args:
        trace_id: Trace identifier
        
    Returns:
        Full ReasoningTrace object
        
    Raises:
        404: If trace not found
    """
    trace = await service.retrieve(trace_id)
    
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    
    return trace


@router.get("/trace", response_model=list)
async def list_traces(
    request_id: str = Query(..., description="Request ID to search"),
    service: TraceService = Depends(get_trace_service)
) -> list:
    """List traces for a request.
    
    Args:
        request_id: Request ID to search
        
    Returns:
        List of trace summaries
    """
    traces = await service.list_by_request(request_id)
    
    # Return summaries only
    return [
        {
            "trace_id": t.trace_id,
            "request_id": t.request_id,
            "created_at": t.created_at.isoformat(),
            "decision_type": t.decision_type,
            "confidence": t.confidence.overall_confidence if t.confidence else None,
            "safety_status": t.safety_check.status.value if t.safety_check else None
        }
        for t in traces
    ]


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackPayload,
    service: FeedbackService = Depends(get_feedback_service)
) -> FeedbackResponse:
    """Submit feedback for an explanation.
    
    Feedback is stored and routed to the Feedback & Learning Engine
    for model improvement.
    
    Args:
        feedback: Feedback payload with trace ID and feedback details
        
    Returns:
        Submission result
    """
    logger.info(f"Received feedback for trace {feedback.trace_id}")
    
    result = await service.submit(feedback)
    
    return FeedbackResponse(**result)


@router.get("/feedback/stats", response_model=dict)
async def get_feedback_stats(
    service: FeedbackService = Depends(get_feedback_service)
) -> dict:
    """Get feedback statistics.
    
    Returns aggregated feedback metrics.
    """
    return await service.get_feedback_stats()


@router.get("/strategies", response_model=list)
async def list_strategies(
    service: ExplanationService = Depends(get_explanation_service)
) -> list:
    """List available explanation strategies.
    
    Returns list of supported explanation strategy types.
    """
    return service.get_supported_strategies()


@router.delete("/trace/{trace_id}")
async def delete_trace(
    trace_id: str,
    service: TraceService = Depends(get_trace_service)
) -> dict:
    """Delete a trace (for GDPR compliance).
    
    Args:
        trace_id: Trace ID to delete
        
    Returns:
        Deletion result
    """
    deleted = await service.delete(trace_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    
    return {"deleted": True, "trace_id": trace_id}
