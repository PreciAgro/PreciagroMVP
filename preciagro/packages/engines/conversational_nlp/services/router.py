"""Tool and engine routing layer."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Tuple

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from ..core.config import settings
from ..models import ChatMessageRequest, IntentResult, ToolCallRecord
from .tracing import start_span


logger = logging.getLogger(__name__)


class EngineRouter:
    """Routes intents to engine connectors with graceful degradation."""

    def __init__(self) -> None:
        self.timeout = settings.engine_timeout_seconds

    async def route(
        self, intent: IntentResult, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], List[ToolCallRecord]]:
        """Fan out to connectors suggested by intent."""
        outputs: Dict[str, Any] = {}
        calls: List[ToolCallRecord] = []

        if intent.intent == "plan_planting":
            geo, call = await self._call_geo_context(request)
            outputs["geo_context"] = geo
            calls.append(call)

            temporal, call = await self._call_temporal_logic(intent, request)
            outputs["temporal_logic"] = temporal
            calls.append(call)

            crop, call = await self._call_crop_intelligence(intent, request)
            outputs["crop_intelligence"] = crop
            calls.append(call)

        elif intent.intent == "diagnose_disease":
            image_used = any(att.type == "image" for att in request.attachments)
            image_result, call = await self._call_image_analysis(request) if image_used else ({}, ToolCallRecord(engine="image-analysis", status="skipped"))
            outputs["image_analysis"] = image_result
            calls.append(call)

            crop, call = await self._call_crop_intelligence(intent, request)
            outputs["crop_intelligence"] = crop
            calls.append(call)

        elif intent.intent == "inventory_status":
            inventory, call = await self._call_inventory(request)
            outputs["inventory"] = inventory
            calls.append(call)

        elif intent.intent == "check_weather":
            geo, call = await self._call_geo_context(request)
            outputs["geo_context"] = geo
            calls.append(call)

        else:
            calls.append(ToolCallRecord(engine="router", status="no-tools"))

        return outputs, calls

    async def _call_geo_context(
        self, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord]:
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
        )

    async def _call_temporal_logic(
        self, intent: IntentResult, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord]:
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
        )

    async def _call_crop_intelligence(
        self, intent: IntentResult, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord]:
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
        )

    async def _call_image_analysis(
        self, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord]:
        image_urls = [att.url for att in request.attachments if att.type == "image" and att.url]
        return await self._safe_post(
            name="image-analysis",
            url=settings.image_analysis_url,
            payload={"images": image_urls},
            stub={
                "diagnosis": "Low-confidence stub result; upload and configure IMAGE_ANALYSIS_URL for live scoring.",
                "confidence": 0.25,
            },
        )

    async def _call_inventory(
        self, request: ChatMessageRequest
    ) -> Tuple[Dict[str, Any], ToolCallRecord]:
        return await self._safe_post(
            name="inventory",
            url=settings.inventory_url,
            payload={"user_id": request.user.id, "farm_ids": request.user.farm_ids},
            stub={"status": "unavailable", "notes": "Inventory engine not configured; returning stub."},
        )

    async def _safe_post(
        self, name: str, url: str, payload: Dict[str, Any], stub: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], ToolCallRecord]:
        """POST to connector when configured; otherwise serve stub."""
        if not url:
            return stub, ToolCallRecord(engine=name, status="stubbed", latency_ms=0)

        headers: Dict[str, str] = {}
        if settings.internal_api_key:
            headers["X-API-Key"] = settings.internal_api_key

        start = time.perf_counter()
        async def _attempt() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await asyncio.wait_for(
                    client.post(url, json=payload, headers=headers), timeout=self.timeout
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
                    return response.json(), ToolCallRecord(engine=name, status="ok", latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("%s connector failure: %s", name, exc)
            return stub, ToolCallRecord(
                engine=name,
                status="degraded",
                latency_ms=latency_ms,
                error=str(exc),
            )
