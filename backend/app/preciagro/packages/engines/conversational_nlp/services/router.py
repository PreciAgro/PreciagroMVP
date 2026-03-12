"""Tool and engine routing layer."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from ..core.config import settings
from ..models import (
    ChatMessageRequest,
    ErrorCode,
    ErrorDetail,
    IntentResult,
    ToolCallRecord,
    ToolsContext,
)
from .tracing import start_span

logger = logging.getLogger(__name__)


class EngineRouter:
    """Routes intents to engine connectors with graceful degradation."""

    def __init__(self) -> None:
        self.timeout = settings.engine_timeout_seconds

    async def route(
        self, intent: IntentResult, request: ChatMessageRequest
    ) -> Tuple[ToolsContext, List[ToolCallRecord], List[ErrorDetail]]:
        """Fan out to connectors suggested by intent."""
        outputs: Dict[str, Any] = {}
        calls: List[ToolCallRecord] = []
        errors: List[ErrorDetail] = []

        if intent.intent == "plan_planting":
            geo, call, err = await self._call_geo_context(request)
            outputs["geo_context"] = geo
            calls.append(call)
            if err:
                errors.append(err)

            temporal, call, err = await self._call_temporal_logic(intent, request)
            outputs["temporal_logic"] = temporal
            calls.append(call)
            if err:
                errors.append(err)

            crop, call, err = await self._call_crop_intelligence(intent, request)
            outputs["crop_intelligence"] = crop
            calls.append(call)
            if err:
                errors.append(err)

        elif intent.intent == "diagnose_disease":
            image_used = any(att.type == "image" for att in request.attachments)
            if image_used:
                image_result, call, err = await self._call_image_analysis(request)
            else:
                image_result, call, err = (
                    {},
                    ToolCallRecord(engine="image-analysis", status="skipped"),
                    None,
                )
            outputs["image_analysis"] = image_result
            calls.append(call)
            if err:
                errors.append(err)

            crop, call, err = await self._call_crop_intelligence(intent, request)
            outputs["crop_intelligence"] = crop
            calls.append(call)
            if err:
                errors.append(err)

        elif intent.intent == "inventory_status":
            inventory, call, err = await self._call_inventory(request)
            outputs["inventory"] = inventory
            calls.append(call)
            if err:
                errors.append(err)

        elif intent.intent == "check_weather":
            geo, call, err = await self._call_geo_context(request)
            outputs["geo_context"] = geo
            calls.append(call)
            if err:
                errors.append(err)

        else:
            calls.append(ToolCallRecord(engine="router", status="no-tools"))

        return ToolsContext.from_raw(outputs), calls, errors

    async def _call_geo_context(
        self, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord, Optional[ErrorDetail]]:
        if not settings.flag_enable_geo_engine:
            return self._disabled_response(
                engine="geo-context",
                stub={
                    "region": "unknown",
                    "location": request.metadata.get("location") or "unspecified",
                    "confidence": 0.0,
                },
                error=ErrorDetail(
                    code=ErrorCode.UPSTREAM_ENGINE_FAILED,
                    message="Geo engine disabled via FLAG_ENABLE_GEO_ENGINE.",
                    component="geo-context",
                ),
            )
        return await self._safe_post(
            name="geo-context",
            url=settings.geo_context_url,
            payload={
                "field": None,
                "polygon": None,
                "location": {
                    "lat": request.metadata.get("lat"),
                    "lon": request.metadata.get("lon"),
                    "name": request.metadata.get("location"),
                },
                "crop_types": [],
            },
            stub={
                "region": "unknown",
                "location": request.metadata.get("location") or "unspecified",
                "confidence": 0.3,
            },
            request=request,
        )

    async def _call_temporal_logic(
        self, intent: IntentResult, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord, Optional[ErrorDetail]]:
        if not settings.flag_enable_temporal_engine:
            return self._disabled_response(
                engine="temporal-logic",
                stub={
                    "recommended_window": "next 2-3 weeks",
                    "notes": "Temporal engine disabled; using static guidance.",
                },
                error=ErrorDetail(
                    code=ErrorCode.TEMPORAL_ENGINE_TIMEOUT,
                    message="Temporal engine disabled via FLAG_ENABLE_TEMPORAL_ENGINE.",
                    component="temporal-logic",
                ),
            )
        return await self._safe_post(
            name="temporal-logic",
            url=settings.temporal_logic_url,
            payload={
                "intent": intent.intent,
                "entities": intent.entities.model_dump(),
                "session_id": request.session_id,
            },
            stub={
                "recommended_window": "next 2-3 weeks",
                "notes": "Stubbed temporal window; configure TEMPORAL_LOGIC_URL to enable live data.",
            },
            request=request,
            failure_code=ErrorCode.TEMPORAL_ENGINE_TIMEOUT,
        )

    async def _call_crop_intelligence(
        self, intent: IntentResult, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord, Optional[ErrorDetail]]:
        return await self._safe_post(
            name="crop-intelligence",
            url=settings.crop_intelligence_url,
            payload={
                "intent": intent.intent,
                "entities": intent.entities.model_dump(),
                "text": request.text,
            },
            stub={
                "recommendations": [
                    "Use a medium-maturity hybrid suited to your rainfall zone.",
                    "Target plant population of ~55,000 seeds/ha unless local advice differs.",
                ]
            },
            request=request,
        )

    async def _call_image_analysis(
        self, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord, Optional[ErrorDetail]]:
        image_urls = [att.url for att in request.attachments if att.type == "image" and att.url]
        if not settings.flag_enable_image_engine:
            return self._disabled_response(
                engine="image-analysis",
                stub={},
                error=ErrorDetail(
                    code=ErrorCode.IMAGE_ANALYSIS_UNAVAILABLE,
                    message="Image analysis disabled via FLAG_ENABLE_IMAGE_ENGINE.",
                    component="image-analysis",
                ),
            )
        return await self._safe_post(
            name="image-analysis",
            url=settings.image_analysis_url,
            payload={"images": image_urls},
            stub={
                "diagnosis": "Low-confidence stub result; upload and configure IMAGE_ANALYSIS_URL for live scoring.",
                "confidence": 0.25,
            },
            request=request,
            failure_code=ErrorCode.IMAGE_ANALYSIS_UNAVAILABLE,
        )

    async def _call_inventory(
        self, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord, Optional[ErrorDetail]]:
        return await self._safe_post(
            name="inventory",
            url=settings.inventory_url,
            payload={"user_id": request.user.id, "farm_ids": request.user.farm_ids},
            stub={
                "status": "unavailable",
                "notes": "Inventory engine not configured; returning stub.",
            },
            request=request,
        )

    async def _safe_post(
        self,
        name: str,
        url: str,
        payload: Dict[str, Any],
        stub: Dict[str, Any],
        *,
        request: ChatMessageRequest,
        failure_code: ErrorCode | None = None,
    ) -> Tuple[Dict[str, Any], ToolCallRecord, Optional[ErrorDetail]]:
        """POST to connector when configured; otherwise serve stub."""
        if not url:
            return stub, ToolCallRecord(engine=name, status="stubbed", latency_ms=0), None

        headers: Dict[str, str] = {}
        if settings.internal_api_key:
            headers["X-API-Key"] = settings.internal_api_key
        enriched_payload = self._inject_identity(payload, request)

        start = time.perf_counter()

        async def _attempt() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await asyncio.wait_for(
                    client.post(url, json=enriched_payload, headers=headers), timeout=self.timeout
                )
                resp.raise_for_status()
                return resp

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(settings.engine_retry_attempts),
                wait=wait_fixed(settings.engine_retry_backoff_seconds),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt, start_span(f"connector_{name}"):
                    response = await _attempt()
                    latency_ms = int((time.perf_counter() - start) * 1000)
                    logger.info("%s connector success", name)
                    return (
                        response.json(),
                        ToolCallRecord(engine=name, status="ok", latency_ms=latency_ms),
                        None,
                    )
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("%s connector failure: %s", name, exc)
            error_code = failure_code or ErrorCode.UPSTREAM_ENGINE_FAILED
            if name == "temporal-logic" and isinstance(exc, asyncio.TimeoutError):
                error_code = ErrorCode.TEMPORAL_ENGINE_TIMEOUT
            if name == "image-analysis":
                error_code = ErrorCode.IMAGE_ANALYSIS_UNAVAILABLE
            return (
                stub,
                ToolCallRecord(
                    engine=name,
                    status="degraded",
                    latency_ms=latency_ms,
                    error=str(exc),
                ),
                ErrorDetail(
                    code=error_code,
                    message=f"{name} connector error: {exc}",
                    component=name,
                ),
            )

    def _inject_identity(
        self, payload: Dict[str, Any], request: ChatMessageRequest
    ) -> Dict[str, Any]:
        enriched = dict(payload)
        enriched.setdefault("tenant_id", request.tenant_id)
        enriched.setdefault("farm_id", request.farm_id)
        enriched.setdefault("user_id", request.user_id)
        enriched.setdefault("user_role", request.user_role)
        enriched.setdefault("channel", request.channel)
        enriched.setdefault("session_id", request.session_id)
        return enriched

    def _disabled_response(
        self,
        *,
        engine: str,
        stub: Dict[str, Any],
        error: ErrorDetail,
    ) -> Tuple[Dict[str, Any], ToolCallRecord, ErrorDetail]:
        return stub, ToolCallRecord(engine=engine, status="disabled", latency_ms=0), error
