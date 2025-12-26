"""Learning Routes - Outbound endpoints for learning signals.

These endpoints are called by internal engines:
- Evaluation & Benchmarking Engine
- Model Orchestration Engine
- PIE Lite (Product Insights Engine)

Signals are pulled, not pushed, for consumption.
"""

import logging
from typing import Optional, Literal
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..contracts.downstream import LearningSignalOutput, SignalType
from ..services.signal_service import SignalService
from ..services.routing_service import RoutingService
from ..services.weighting_service import WeightingService
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["Learning Signals"])

# Service instances
signal_service = SignalService()
routing_service = RoutingService()
weighting_service = WeightingService()


class SignalsResponse(BaseModel):
    """Response for signals query."""

    signals: list[LearningSignalOutput]
    count: int
    has_more: bool
    engine: str


class SignalExportRequest(BaseModel):
    """Request for signal export."""

    engine: Literal["model_orchestration", "evaluation"] = Field(..., description="Target engine")
    region_code: Optional[str] = Field(None, description="Optional region filter")
    signal_types: Optional[list[str]] = Field(None, description="Filter by signal types")
    min_strength: Optional[float] = Field(None, ge=0, le=1, description="Min signal strength")
    limit: int = Field(default=100, ge=1, le=1000, description="Max signals to export")
    mark_as_exported: bool = Field(default=True, description="Mark signals as exported")


class ExportResponse(BaseModel):
    """Response for signal export."""

    export_id: str
    engine: str
    signal_count: int
    signals: list[LearningSignalOutput]
    exported_at: datetime


class StatsResponse(BaseModel):
    """Response for learning stats."""

    total_signals: int
    unrouted_signals: int
    by_type: dict
    by_engine: dict
    routing_stats: dict


@router.get("/signals", response_model=SignalsResponse)
async def get_learning_signals(
    engine: Literal["evaluation", "model_orchestration", "pie"] = Query(
        ..., description="Target engine to get signals for"
    ),
    region: Optional[str] = Query(None, description="Optional region filter"),
    limit: int = Query(100, ge=1, le=500, description="Max signals to return"),
):
    """Get learning signals targeted for a specific engine.

    Called by downstream engines to pull their signals.
    Only returns unrouted signals.
    """
    try:
        signals = await signal_service.get_signals_for_engine(
            engine=engine,
            region=region,
            limit=limit,
        )

        # Convert to output format
        outputs = [
            LearningSignalOutput(
                signal_id=s.signal_id,
                version=s.version,
                signal_type=s.signal_type,
                signal_strength=s.signal_strength,
                source_feedback_ids=s.source_feedback_ids,
                recommendation_id=s.recommendation_id,
                reasoning_trace_id=s.reasoning_trace_id,
                target_engine=s.target_engine,
                region_scope=s.region_scope,
                cross_region_propagation=s.cross_region_propagation,
                model_id=s.model_id,
                model_version=s.model_version,
                feedback_count=s.feedback_count,
                average_weight=s.average_weight,
                confidence_score=s.confidence_score,
                feedback_window_start=s.feedback_window_start,
                feedback_window_end=s.feedback_window_end,
                correlation_id=s.correlation_id,
                audit_trace_id=s.audit_trace_id,
                context=s.context,
            )
            for s in signals
        ]

        # Check if there are more
        total = await signal_service.get_unrouted_count(engine)
        has_more = total > len(signals)

        return SignalsResponse(
            signals=outputs,
            count=len(outputs),
            has_more=has_more,
            engine=engine,
        )

    except Exception as e:
        logger.error(f"Failed to get signals for {engine}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get signals: {str(e)}")


@router.post("/export/model-orchestration", response_model=ExportResponse)
async def export_for_model_orchestration(
    request: SignalExportRequest,
):
    """Export learning signals for Model Orchestration Engine.

    Provides signals relevant for model retraining decisions.
    """
    if request.engine != "model_orchestration":
        request.engine = "model_orchestration"

    return await _perform_export(request)


@router.post("/export/evaluation", response_model=ExportResponse)
async def export_for_evaluation(
    request: SignalExportRequest,
):
    """Export learning signals for Evaluation & Benchmarking Engine.

    Provides signals for model evaluation and quality metrics.
    """
    if request.engine != "evaluation":
        request.engine = "evaluation"

    return await _perform_export(request)


async def _perform_export(request: SignalExportRequest) -> ExportResponse:
    """Perform signal export for an engine.

    Args:
        request: Export request

    Returns:
        ExportResponse with signals
    """
    from uuid import uuid4

    try:
        # Get signals
        signals = await signal_service.get_signals_for_engine(
            engine=request.engine,
            region=request.region_code,
            limit=request.limit,
        )

        # Filter by signal types if specified
        if request.signal_types:
            type_set = set(request.signal_types)
            signals = [s for s in signals if s.signal_type.value in type_set]

        # Filter by min strength if specified
        if request.min_strength is not None:
            signals = [s for s in signals if s.signal_strength >= request.min_strength]

        # Apply limit again after filtering
        signals = signals[: request.limit]

        # Convert to output format
        outputs = [
            LearningSignalOutput(
                signal_id=s.signal_id,
                version=s.version,
                signal_type=s.signal_type,
                signal_strength=s.signal_strength,
                source_feedback_ids=s.source_feedback_ids,
                recommendation_id=s.recommendation_id,
                reasoning_trace_id=s.reasoning_trace_id,
                target_engine=s.target_engine,
                region_scope=s.region_scope,
                cross_region_propagation=s.cross_region_propagation,
                model_id=s.model_id,
                model_version=s.model_version,
                feedback_count=s.feedback_count,
                average_weight=s.average_weight,
                confidence_score=s.confidence_score,
                feedback_window_start=s.feedback_window_start,
                feedback_window_end=s.feedback_window_end,
                correlation_id=s.correlation_id,
                audit_trace_id=s.audit_trace_id,
                context=s.context,
            )
            for s in signals
        ]

        # Mark as exported/routed if requested
        if request.mark_as_exported and signals:
            stream = (
                settings.STREAM_MODEL_ORCHESTRATION
                if request.engine == "model_orchestration"
                else settings.STREAM_EVALUATION
            )
            await signal_service.mark_routed(
                [s.signal_id for s in signals],
                stream,
            )

        return ExportResponse(
            export_id=str(uuid4()),
            engine=request.engine,
            signal_count=len(outputs),
            signals=outputs,
            exported_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to export signals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export signals: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_learning_stats():
    """Get learning signal statistics."""
    try:
        # Get signal stats
        all_signals = list(signal_service._signal_store.values())

        # Count by type
        by_type = {}
        for signal in all_signals:
            t = signal.signal_type.value
            by_type[t] = by_type.get(t, 0) + 1

        # Count by target engine
        by_engine = {}
        for signal in all_signals:
            e = signal.target_engine
            by_engine[e] = by_engine.get(e, 0) + 1

        # Unrouted count
        unrouted = await signal_service.get_unrouted_count()

        # Routing stats
        routing_stats = routing_service.get_routing_stats()

        return StatsResponse(
            total_signals=len(all_signals),
            unrouted_signals=unrouted,
            by_type=by_type,
            by_engine=by_engine,
            routing_stats=routing_stats,
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/signal/{signal_id}")
async def get_signal_by_id(signal_id: str):
    """Get a specific learning signal by ID."""
    signal = await signal_service.get_signal(signal_id)

    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

    return LearningSignalOutput(
        signal_id=signal.signal_id,
        version=signal.version,
        signal_type=signal.signal_type,
        signal_strength=signal.signal_strength,
        source_feedback_ids=signal.source_feedback_ids,
        recommendation_id=signal.recommendation_id,
        reasoning_trace_id=signal.reasoning_trace_id,
        target_engine=signal.target_engine,
        region_scope=signal.region_scope,
        cross_region_propagation=signal.cross_region_propagation,
        model_id=signal.model_id,
        model_version=signal.model_version,
        feedback_count=signal.feedback_count,
        average_weight=signal.average_weight,
        confidence_score=signal.confidence_score,
        feedback_window_start=signal.feedback_window_start,
        feedback_window_end=signal.feedback_window_end,
        correlation_id=signal.correlation_id,
        audit_trace_id=signal.audit_trace_id,
        context=signal.context,
    )
