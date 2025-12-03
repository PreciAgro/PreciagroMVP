"""AgroLLM client interface with pluggable backends and deterministic stub."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Protocol

import httpx

from ..core.config import Settings
from ..models import (
    ChatMessageRequest,
    Citation,
    IntentEntities,
    IntentResult,
    SessionContext,
    StructuredAnswer,
    ToolsContext,
)

logger = logging.getLogger(__name__)


class AgroLLMBackend(Protocol):
    """Protocol for AgroLLM backends."""

    name: str

    async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return structured classification JSON."""

    async def generate(self, payload: Dict[str, Any]) -> Optional[Any]:
        """Return structured generation payload (dict or JSON string)."""


class HTTPAgroLLMBackend:
    """Backend that proxies to remote HTTP endpoints."""

    name = "http"

    def __init__(
        self,
        classify_url: str | None,
        generate_url: str | None,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        self.classify_url = (classify_url or "").strip() or None
        self.generate_url = (generate_url or "").strip() or None
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self.classify_url or self.generate_url)

    async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.classify_url:
            return None
        return await self._post(self.classify_url, payload)

    async def generate(self, payload: Dict[str, Any]) -> Optional[Any]:
        if not self.generate_url:
            return None
        return await self._post(self.generate_url, payload)

    async def _post(self, url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else {"text": data}
        except Exception as exc:  # noqa: BLE001
            logger.warning("AgroLLM HTTP backend request failed: %s", exc)
            return None


class StubAgroLLMBackend:
    """Deterministic backend used in lieu of a real model."""

    name = "stub"

    async def classify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        message: Dict[str, Any] = payload.get("message", {})
        text = str(message.get("text", "")).lower()
        metadata = message.get("metadata") or {}

        intent = "general_question"
        if any(word in text for word in ("plant", "sow", "planting", "seed")):
            intent = "plan_planting"
        elif any(word in text for word in ("disease", "spot", "leaf", "symptom")):
            intent = "diagnose_disease"
        elif any(word in text for word in ("weather", "rain", "forecast", "rainfall")):
            intent = "check_weather"
        elif any(word in text for word in ("inventory", "stock", "warehouse", "input")):
            intent = "inventory_status"
        elif any(word in text for word in ("price", "market", "sell", "buy")):
            intent = "market_prices"

        entities: Dict[str, Any] = {
            "crop": self._extract_crop(text),
            "location": metadata.get("location"),
            "season_or_date": metadata.get("season"),
            "problem_type": "leaf symptom" if "leaf" in text else None,
            "urgency": "high" if "urgent" in text or "asap" in text else "normal",
            "language": metadata.get("locale"),
            "field_name": metadata.get("field"),
        }
        return {
            "intent": intent,
            "entities": entities,
            "confidence": 0.65,
            "schema_version": payload.get("schema_version", "v0"),
        }

    async def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        intent = payload.get("intent", {}).get("intent", "general_question")
        message = payload.get("message", {})
        tools = payload.get("tools_context", {})
        rag_context = payload.get("rag_context", [])

        summary = self._summary_from_tools(intent, message.get("text", ""), tools)
        steps = self._steps_from_tools(intent, tools)
        warnings = ["Always verify against local regulations and labels."]
        extras: Dict[str, Any] = {}
        if rag_context:
            extras["citations"] = [item.get("id") for item in rag_context]
        return {
            "summary": summary,
            "steps": steps,
            "warnings": warnings,
            "extras": extras,
        }

    @staticmethod
    def _extract_crop(text: str) -> Optional[str]:
        for crop in ("maize", "corn", "wheat", "soy", "soybean", "sorghum", "rice"):
            if crop in text:
                return "maize" if crop == "corn" else crop
        return None

    @staticmethod
    def _summary_from_tools(intent: str, user_text: str, tools: Dict[str, Any]) -> str:
        if intent == "plan_planting":
            window = tools.get("temporal_logic", {}).get("recommended_window", "the next planting window")
            region = tools.get("geo_context", {}).get("region", "your area")
            return f"Plan to plant in {region} during {window}. User asked: {user_text[:80]}."
        if intent == "diagnose_disease":
            diagnosis = tools.get("crop_intelligence", {}).get("diagnosis") or tools.get("image_analysis", {}).get("diagnosis")
            diagnosis = diagnosis or "symptoms require inspection."
            return f"Preliminary diagnosis: {diagnosis}"
        if intent == "inventory_status":
            return "Inventory feed unavailable; confirm latest warehouse counts manually."
        if intent == "check_weather":
            return "Weather guidance: wait for a 20-30mm forecast before field operations."
        return "General advisory: share more context for better guidance."

    @staticmethod
    def _steps_from_tools(intent: str, tools: Dict[str, Any]) -> List[str]:
        if intent == "plan_planting":
            steps = ["Ensure soil moisture is adequate.", "Treat seed before planting.", "Calibrate planter for uniform stands."]
            recs = tools.get("crop_intelligence", {}).get("recommendations")
            if isinstance(recs, list):
                steps.extend(recs[:2])
            return steps
        if intent == "diagnose_disease":
            steps = ["Inspect affected plants and capture photos.", "Consult local agronomist before spraying."]
            diag = tools.get("image_analysis", {}).get("diagnosis")
            if diag:
                steps.insert(0, f"Image analysis suggests: {diag}")
            return steps
        if intent == "inventory_status":
            return ["Reconcile seed and fertilizer stock with recent deliveries.", "Set reorder points for two-week buffer."]
        if intent == "check_weather":
            return ["Check forecast for next 7 days.", "Delay planting until soil moisture is stable."]
        return ["Collect additional data from field sensors or notes."]


class AgroLLMClient:
    """High-level interface used by the conversational engine."""

    def __init__(self, backend: AgroLLMBackend, fallback_backend: Optional[AgroLLMBackend] = None) -> None:
        self.backend = backend
        self.fallback_backend = fallback_backend or StubAgroLLMBackend()

    @property
    def backend_name(self) -> str:
        return getattr(self.backend, "name", "unknown")

    @property
    def has_remote_backend(self) -> bool:
        return isinstance(self.backend, HTTPAgroLLMBackend) and self.backend.available

    async def classify_intent_and_entities(
        self,
        request: ChatMessageRequest,
        session_context: SessionContext,
        schema_version: str = "v0",
    ) -> Optional[IntentResult]:
        payload = self._build_classification_payload(request, session_context, schema_version)
        response = await self.backend.classify(payload)
        if not response and self.fallback_backend:
            response = await self.fallback_backend.classify(payload)
        return self._parse_intent_response(response)

    async def generate_answer(
        self,
        request: ChatMessageRequest,
        intent: IntentResult,
        session_context: SessionContext,
        tools_context: ToolsContext,
        rag_context: List[Citation],
        system_prompt: str,
    ) -> Optional[StructuredAnswer]:
        payload = self._build_generation_payload(
            request=request,
            intent=intent,
            session_context=session_context,
            tools_context=tools_context,
            rag_context=rag_context,
            system_prompt=system_prompt,
        )
        response = await self.backend.generate(payload)
        if response is None and self.fallback_backend:
            response = await self.fallback_backend.generate(payload)
        return self._parse_generation_response(response)

    def _build_classification_payload(
        self,
        request: ChatMessageRequest,
        session_context: SessionContext,
        schema_version: str,
    ) -> Dict[str, Any]:
        instructions = (
            "You classify farmer support messages into intents such as plan_planting, "
            "diagnose_disease, check_weather, inventory_status, market_prices, general_question. "
            "Respond with strict JSON using keys intent, entities, confidence, schema_version. "
            "Entities include crop, location, field_name, season_or_date, problem_type, urgency, language."
        )
        prompt = {
            "instructions": instructions,
            "message": request.model_dump(),
            "session_context": session_context.model_dump(),
            "examples": [
                {
                    "user": "When should I plant maize in Murewa?",
                    "intent": "plan_planting",
                    "entities": {"crop": "maize", "location": "Murewa"},
                },
                {
                    "user": "Leaves have yellow stripes, what should I spray?",
                    "intent": "diagnose_disease",
                    "entities": {"problem_type": "leaf symptom"},
                },
            ],
        }
        return {
            "prompt": json.dumps(prompt),
            "schema_version": schema_version,
            "message": request.model_dump(),
            "session_context": session_context.model_dump(),
        }

    def _build_generation_payload(
        self,
        *,
        request: ChatMessageRequest,
        intent: IntentResult,
        session_context: SessionContext,
        tools_context: ToolsContext,
        rag_context: List[Citation],
        system_prompt: str,
    ) -> Dict[str, Any]:
        prompt_sections = [
            system_prompt,
            f"User message: {request.text}",
            f"Intent: {intent.intent}",
            f"Entities: {intent.entities.model_dump()}",
            "Session turns:",
        ]
        for turn in session_context.turns[-5:]:
            prompt_sections.append(f"- {turn.role}: {turn.text[:180]}")
        prompt_sections.append(f"Tools context: {tools_context.as_dict()}")
        if rag_context:
            prompt_sections.append("RAG snippets:")
            for citation in rag_context:
                prompt_sections.append(f"- [{citation.id}] {citation.snippet}")
        prompt_sections.append(
            "Output JSON with keys summary, steps (array), warnings (array), extras (array). "
            "Steps must be actionable. Include citation ids inside brackets when referencing RAG snippets."
        )
        return {
            "prompt": "\n".join(prompt_sections),
            "message": request.model_dump(),
            "intent": intent.model_dump(),
            "session_context": session_context.model_dump(),
            "tools_context": tools_context.as_dict(),
            "rag_context": [citation.model_dump() for citation in rag_context],
        }

    @staticmethod
    def _parse_intent_response(data: Optional[Dict[str, Any]]) -> Optional[IntentResult]:
        if not data:
            return None
        intent = data.get("intent")
        if not intent:
            return None
        entities_raw = data.get("entities", {})
        entities = IntentEntities(**entities_raw) if isinstance(entities_raw, dict) else IntentEntities()
        try:
            confidence = float(data.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        schema_version = str(data.get("schema_version", "v0"))
        return IntentResult(intent=intent, entities=entities, confidence=confidence, schema_version=schema_version)

    @staticmethod
    def _parse_generation_response(data: Optional[Any]) -> Optional[StructuredAnswer]:
        if data is None:
            return None
        parsed: Dict[str, Any]
        if isinstance(data, dict):
            parsed = data
        else:
            try:
                parsed = json.loads(str(data))
            except json.JSONDecodeError:
                parsed = {"summary": str(data)}
        summary = str(parsed.get("summary") or parsed.get("text") or parsed.get("answer") or "")
        if not summary:
            return None
        steps = parsed.get("steps") if isinstance(parsed.get("steps"), list) else []
        warnings = parsed.get("warnings") if isinstance(parsed.get("warnings"), list) else []
        extras_raw = parsed.get("extras")
        if isinstance(extras_raw, dict):
            extras = extras_raw
        elif extras_raw:
            extras = {"notes": extras_raw}
        else:
            extras = {}
        return StructuredAnswer(summary=summary, steps=steps, warnings=warnings, extras=extras, raw_text=str(data))


def build_agrollm_client(config: Settings) -> AgroLLMClient:
    """Factory that selects HTTP or stub backend based on settings."""
    backend_choice = (config.agrollm_backend or "").lower()
    http_backend = HTTPAgroLLMBackend(
        classify_url=config.agrollm_classify_url,
        generate_url=config.agrollm_generate_url,
        api_key=config.agrollm_api_key,
        timeout_seconds=config.agrollm_timeout_seconds,
    )
    if backend_choice in {"http", "remote"} and http_backend.available:
        return AgroLLMClient(backend=http_backend, fallback_backend=StubAgroLLMBackend())
    if backend_choice not in {"stub", ""} and http_backend.available:
        return AgroLLMClient(backend=http_backend, fallback_backend=StubAgroLLMBackend())
    return AgroLLMClient(backend=StubAgroLLMBackend())
