"""FastAPI routes for Geo Context Engine."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from ...config import settings

os.environ.setdefault("DEV_MODE", "true")

from preciagro.packages.shared.security import (
    TenantContext,  # noqa: E402
    require_scopes,
    sanitize_for_logs,
    validate_polygon_size,
)

from ...contracts.v1.fco import FCOResponse  # noqa: E402
from ...contracts.v1.requests import FCORequest  # noqa: E402
from ...pipeline.resolver import GeoContextResolver  # noqa: E402
from ...storage.db import get_cached_fco_by_hash  # noqa: E402

logger = logging.getLogger(__name__)
router = APIRouter()

RESOLVE_SCOPE = "geo-context:resolve"
READ_SCOPE = "geo-context:read"


async def _resolve_handler(
    request: FCORequest,
    tenant_ctx: TenantContext = Depends(require_scopes(RESOLVE_SCOPE)),
) -> FCOResponse:
    try:
        coords = None
        if request.field and request.field.coordinates:
            coords = request.field.coordinates
        elif request.polygon and request.polygon.coordinates:
            coords = [request.polygon.coordinates]
        if coords:
            validate_polygon_size(coords, max_area_ha=settings.MAX_POLYGON_AREA)

        logger.info(
            "geo-context resolve request",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "request": sanitize_for_logs(request.model_dump()),
                "crop_types": request.crop_types,
            },
        )

        resolver = GeoContextResolver()
        try:
            result = await resolver.resolve_field_context(request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        logger.info(
            "geo-context resolve success",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "context_hash": result.context_hash,
                "confidence_score": result.confidence_score,
                "processing_time_ms": result.processing_time_ms,
            },
        )

        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "geo-context resolve failure",
            extra={
                "tenant_id": tenant_ctx.tenant_id,
                "error": str(exc),
                "request": sanitize_for_logs(request.model_dump()),
            },
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _get_cached_handler(
    context_hash: str,
    tenant_ctx: TenantContext = Depends(require_scopes(READ_SCOPE)),
) -> FCOResponse:
    cached = await get_cached_fco_by_hash(context_hash)
    if not cached:
        raise HTTPException(status_code=404, detail="FCO not found")

    logger.info(
        "geo-context cache hit",
        extra={"tenant_id": tenant_ctx.tenant_id, "context_hash": context_hash},
    )
    return cached


async def _health_handler() -> dict[str, str]:
    return {"status": "healthy", "service": "geo-context"}


async def _version_handler() -> dict[str, str]:
    return {"version": "1.0.0", "service": "geo-context"}


# Register routes under both legacy and new paths to satisfy tests and clients.
router.add_api_route(
    "/geo-context/fco",
    _resolve_handler,
    methods=["POST"],
    response_model=FCOResponse,
    tags=["geo-context"],
)
router.add_api_route(
    "/v1/resolve",
    _resolve_handler,
    methods=["POST"],
    response_model=FCOResponse,
    tags=["geo-context"],
)

router.add_api_route(
    "/geo-context/fco/{context_hash}",
    _get_cached_handler,
    methods=["GET"],
    response_model=FCOResponse,
    tags=["geo-context"],
)

router.add_api_route("/geo-context/health", _health_handler, methods=["GET"], tags=["geo-context"])
router.add_api_route("/health", _health_handler, methods=["GET"], tags=["geo-context"])

router.add_api_route(
    "/geo-context/version", _version_handler, methods=["GET"], tags=["geo-context"]
)
router.add_api_route("/version", _version_handler, methods=["GET"], tags=["geo-context"])
