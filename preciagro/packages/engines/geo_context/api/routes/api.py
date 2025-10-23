"""FastAPI routes for Geo Context Engine."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from ...contracts.v1.requests import FCORequest
from ...contracts.v1.fco import FCOResponse
from ...pipeline.resolver import GeoContextResolver
from preciagro.packages.shared.security import require_scopes, TenantContext, validate_polygon_size, sanitize_for_logs
import logging

router = APIRouter(prefix="/geocontext", tags=["geocontext"])
logger = logging.getLogger(__name__)


@router.post("/resolve", response_model=FCOResponse)
async def resolve_field_context(
    request: FCORequest,
    tenant_ctx: TenantContext = Depends(require_scopes("geocontext:resolve"))
) -> FCOResponse:
    """Resolve Field Context Object (FCO) for a given location."""
    try:
        # Input validation and guardrails
        if request.field and hasattr(request.field, 'coordinates'):
            validate_polygon_size(request.field.coordinates)

        # Log request (sanitized)
        logger.info(
            "FCO resolve request",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "request": sanitize_for_logs(request.dict()),
                "crops": request.crops
            }
        )

        resolver = GeoContextResolver()
        result = await resolver.resolve_field_context(request)

        # Log successful resolution
        logger.info(
            "FCO resolved successfully",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "context_hash": getattr(result, 'context_hash', None),
                "confidence": result.confidence,
                "processing_time_ms": result.processing_time_ms
            }
        )

        return result
    except Exception as e:
        logger.error(
            "FCO resolve failed",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "error": str(e),
                "request": sanitize_for_logs(request.dict())
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fco/{context_hash}")
async def get_cached_field_context(
    context_hash: str,
    tenant_ctx: TenantContext = Depends(require_scopes("geocontext:read"))
) -> FCOResponse:
    """Get cached Field Context Object by context hash."""
    try:
        from ...storage.db import get_cached_fco_by_hash

        result = await get_cached_fco_by_hash(context_hash)
        if not result:
            raise HTTPException(status_code=404, detail="FCO not found")

        logger.info(
            "FCO retrieved from cache",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "context_hash": context_hash
            }
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "FCO cache retrieval failed",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "context_hash": context_hash,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "geocontext"}


@router.get("/version")
async def version() -> Dict[str, str]:
    """Version endpoint."""
    return {"version": "1.0.0", "service": "geocontext"}
