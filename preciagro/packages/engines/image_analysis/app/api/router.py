"""v1 API routes for the Image Analysis Engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from preciagro.packages.shared.security.deps import get_tenant_context, TenantContext

from ..core import settings
from ..models import (
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    HealthResponse,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
)
from ..services import ImageAnalysisService

router = APIRouter(prefix=settings.API_PREFIX, tags=["image-analysis"])
service = ImageAnalysisService()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    include_in_schema=False,
)
async def health() -> HealthResponse:
    """Return a simple readiness payload for probes and dashboards."""

    return HealthResponse(
        service=settings.APP_NAME,
        status="ready",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.post(
    "/analyze-image",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a single crop image",
)
async def analyze_image(
    payload: ImageAnalysisRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ImageAnalysisResponse:
    """Run the (placeholder) analysis pipeline and return the standard response contract."""

    return service.analyze(payload)


@router.post(
    "/batch",
    response_model=BatchAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a batch of crop images",
)
async def analyze_batch(
    payload: BatchAnalysisRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BatchAnalysisResponse:
    """Run the analysis pipeline over a batch of requests."""

    responses = [service.analyze(item) for item in payload.items]
    return BatchAnalysisResponse(items=responses)
