"""API router for Diagnosis & Recommendation Engine."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from ..contracts.v1.schemas import DREInput, DREResponse
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dre", tags=["diagnosis-recommendation"])


@router.post("/diagnose", response_model=DREResponse)
async def diagnose(
    input_data: DREInput,
    # auth: Optional[str] = Depends(get_auth_token),  # TODO: Add auth
) -> DREResponse:
    """
    Main diagnosis and recommendation endpoint.

    Accepts structured inputs from upstream engines and returns
    ranked diagnoses with validated recommendation plans.
    """
    try:
        from ..services.engine import DiagnosisRecommendationEngine

        engine = DiagnosisRecommendationEngine()
        response = await engine.process(input_data)

        return response

    except Exception as e:
        logger.error(f"Error processing diagnosis request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Internal error processing diagnosis: {str(e)}"
        )


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "diagnosis-recommendation",
        "version": settings.VERSION,
    }


@router.get("/status")
async def status():
    """Engine status and configuration."""
    return {
        "service": "diagnosis-recommendation",
        "version": settings.VERSION,
        "config": {
            "max_hypotheses": settings.MAX_HYPOTHESES,
            "min_confidence_threshold": settings.MIN_CONFIDENCE_THRESHOLD,
            "enable_safety_validation": settings.ENABLE_SAFETY_VALIDATION,
            "enable_constraint_checking": settings.ENABLE_CONSTRAINT_CHECKING,
        },
        "adapters": {
            "cv": settings.ENABLE_CV_ADAPTER,
            "nlp": settings.ENABLE_NLP_ADAPTER,
            "llm": settings.ENABLE_LLM_ADAPTER,
            "rl": settings.ENABLE_RL_ADAPTER,
            "graph": settings.ENABLE_GRAPH_ADAPTER,
        },
    }
