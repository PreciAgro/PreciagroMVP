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


class OpenAIBackend:
    """Backend for OpenAI API (GPT-4, GPT-3.5, etc.)."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        classify_model: str | None = None,
        generate_model: str | None = None,
        timeout_seconds: float = 30.0,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.classify_model = classify_model or model
        self.generate_model = generate_model or model
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url or "https://api.openai.com/v1"
        # TODO: Import openai library when ready
        # import openai
        # self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        TODO: Implement OpenAI classification call.
        
        Expected payload structure:
        - prompt: JSON string with instructions, message, session_context, examples
        
        Expected response format:
        {
            "intent": "plan_planting",
            "entities": {"crop": "maize", "location": "Murewa"},
            "confidence": 0.85,
            "schema_version": "v0"
        }
        
        Implementation steps:
        1. Parse prompt from payload
        2. Build OpenAI chat completion request with system/user messages
        3. Use JSON mode or function calling to ensure structured output
        4. Parse and validate response
        5. Return structured dict or None on error
        """
        if not self.available:
            return None
        # TODO: Replace with actual OpenAI API call
        # Example structure:
        # response = await self.client.chat.completions.create(
        #     model=self.classify_model,
        #     messages=[
        #         {"role": "system", "content": "You are an intent classifier..."},
        #         {"role": "user", "content": payload.get("prompt", "")}
        #     ],
        #     response_format={"type": "json_object"},
        #     temperature=0.1
        # )
        # return json.loads(response.choices[0].message.content)
        logger.warning("OpenAI backend not yet implemented - returning None")
        return None

    async def generate(self, payload: Dict[str, Any]) -> Optional[Any]:
        """
        TODO: Implement OpenAI generation call.
        
        Expected payload structure:
        - prompt: Full prompt string with system/user/tools/RAG context
        - message, intent, session_context, tools_context, rag_context
        
        Expected response format:
        {
            "summary": "Main answer text",
            "steps": ["step1", "step2"],
            "warnings": ["warning1"],
            "extras": {}
        }
        
        Implementation steps:
        1. Build chat messages from prompt and context
        2. Call OpenAI chat completion with appropriate model
        3. Use JSON mode for structured output
        4. Parse and return structured dict
        """
        if not self.available:
            return None
        # TODO: Replace with actual OpenAI API call
        logger.warning("OpenAI backend not yet implemented - returning None")
        return None


class AnthropicBackend:
    """Backend for Anthropic Claude API."""

    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-opus-20240229",
        classify_model: str | None = None,
        generate_model: str | None = None,
        timeout_seconds: float = 30.0,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.classify_model = classify_model or model
        self.generate_model = generate_model or model
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url or "https://api.anthropic.com/v1"
        # TODO: Import anthropic library when ready
        # import anthropic
        # self.client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        TODO: Implement Anthropic classification call.
        
        Use Claude's structured output capabilities or prompt engineering
        to return JSON with intent, entities, confidence.
        
        Implementation steps:
        1. Build messages array from payload
        2. Call messages.create() with model and system prompt
        3. Parse JSON from response content
        4. Validate and return structured dict
        """
        if not self.available:
            return None
        # TODO: Replace with actual Anthropic API call
        logger.warning("Anthropic backend not yet implemented - returning None")
        return None

    async def generate(self, payload: Dict[str, Any]) -> Optional[Any]:
        """
        TODO: Implement Anthropic generation call.
        
        Use Claude for response generation with tools/RAG context.
        """
        if not self.available:
            return None
        # TODO: Replace with actual Anthropic API call
        logger.warning("Anthropic backend not yet implemented - returning None")
        return None


class OllamaBackend:
    """Backend for local Ollama models (Llama, Mistral, etc.)."""

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        classify_model: str | None = None,
        generate_model: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.classify_model = classify_model or model
        self.generate_model = generate_model or model
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        # TODO: Add health check to verify Ollama is running
        return True

    async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        TODO: Implement Ollama classification call.
        
        Ollama uses a simple HTTP API:
        POST /api/generate or /api/chat
        
        Implementation steps:
        1. Build prompt from payload
        2. POST to {base_url}/api/chat with model and messages
        3. Parse JSON response (may need to extract JSON from text)
        4. Return structured dict
        
        Note: Ollama models may not always return valid JSON, so add parsing/validation.
        """
        if not self.available:
            return None
        # TODO: Replace with actual Ollama API call
        # Example:
        # async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
        #     response = await client.post(
        #         f"{self.base_url}/api/chat",
        #         json={
        #             "model": self.classify_model,
        #             "messages": [{"role": "user", "content": prompt}],
        #             "format": "json"
        #         }
        #     )
        #     return response.json()
        logger.warning("Ollama backend not yet implemented - returning None")
        return None

    async def generate(self, payload: Dict[str, Any]) -> Optional[Any]:
        """
        TODO: Implement Ollama generation call.
        
        Similar to classify but with full context for response generation.
        """
        if not self.available:
            return None
        # TODO: Replace with actual Ollama API call
        logger.warning("Ollama backend not yet implemented - returning None")
        return None


class VLLMBackend:
    """Backend for vLLM server (high-performance local inference)."""

    name = "vllm"

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model: str | None = None,
        classify_model: str | None = None,
        generate_model: str | None = None,
        timeout_seconds: float = 60.0,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.classify_model = classify_model or model
        self.generate_model = generate_model or model
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key

    @property
    def available(self) -> bool:
        # TODO: Add health check
        return True

    async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        TODO: Implement vLLM classification call.
        
        vLLM typically exposes OpenAI-compatible API at /v1/chat/completions
        
        Implementation steps:
        1. Build OpenAI-format request
        2. POST to {base_url}/v1/chat/completions
        3. Parse response (OpenAI-compatible format)
        4. Extract and parse JSON from content
        """
        if not self.available:
            return None
        # TODO: Replace with actual vLLM API call
        logger.warning("vLLM backend not yet implemented - returning None")
        return None

    async def generate(self, payload: Dict[str, Any]) -> Optional[Any]:
        """
        TODO: Implement vLLM generation call.
        
        Use OpenAI-compatible endpoint for response generation.
        """
        if not self.available:
            return None
        # TODO: Replace with actual vLLM API call
        logger.warning("vLLM backend not yet implemented - returning None")
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
    """
    Factory that selects backend based on AGROLLM_BACKEND setting.
    
    Supported backends:
    - stub: Deterministic fallback (default)
    - http/remote: Generic HTTP endpoints
    - openai: OpenAI API (GPT-4, GPT-3.5, etc.)
    - anthropic: Anthropic Claude API
    - ollama: Local Ollama models
    - vllm: vLLM inference server
    
    See RUNBOOK_LLM_INTEGRATION.md for detailed setup instructions.
    """
    backend_choice = (config.agrollm_backend or "").lower()
    fallback = StubAgroLLMBackend()
    
    # OpenAI backend
    if backend_choice == "openai":
        openai_backend = OpenAIBackend(
            api_key=config.agrollm_api_key or getattr(config, "openai_api_key", ""),
            model=getattr(config, "openai_model", "gpt-4"),
            classify_model=getattr(config, "openai_classify_model", None),
            generate_model=getattr(config, "openai_generate_model", None),
            timeout_seconds=config.agrollm_timeout_seconds,
            base_url=getattr(config, "openai_base_url", None),
        )
        if openai_backend.available:
            return AgroLLMClient(backend=openai_backend, fallback_backend=fallback)
        logger.warning("OpenAI backend configured but API key missing, using stub")
    
    # Anthropic backend
    elif backend_choice == "anthropic":
        anthropic_backend = AnthropicBackend(
            api_key=config.agrollm_api_key or getattr(config, "anthropic_api_key", ""),
            model=getattr(config, "anthropic_model", "claude-3-opus-20240229"),
            classify_model=getattr(config, "anthropic_classify_model", None),
            generate_model=getattr(config, "anthropic_generate_model", None),
            timeout_seconds=config.agrollm_timeout_seconds,
            base_url=getattr(config, "anthropic_base_url", None),
        )
        if anthropic_backend.available:
            return AgroLLMClient(backend=anthropic_backend, fallback_backend=fallback)
        logger.warning("Anthropic backend configured but API key missing, using stub")
    
    # Ollama backend
    elif backend_choice == "ollama":
        ollama_backend = OllamaBackend(
            base_url=getattr(config, "ollama_base_url", "http://localhost:11434"),
            model=getattr(config, "ollama_model", "llama2"),
            classify_model=getattr(config, "ollama_classify_model", None),
            generate_model=getattr(config, "ollama_generate_model", None),
            timeout_seconds=config.agrollm_timeout_seconds,
        )
        return AgroLLMClient(backend=ollama_backend, fallback_backend=fallback)
    
    # vLLM backend
    elif backend_choice == "vllm":
        vllm_backend = VLLMBackend(
            base_url=getattr(config, "vllm_base_url", "http://localhost:8000"),
            model=getattr(config, "vllm_model", None),
            classify_model=getattr(config, "vllm_classify_model", None),
            generate_model=getattr(config, "vllm_generate_model", None),
            timeout_seconds=config.agrollm_timeout_seconds,
            api_key=getattr(config, "vllm_api_key", None),
        )
        return AgroLLMClient(backend=vllm_backend, fallback_backend=fallback)
    
    # HTTP/Remote backend (generic)
    elif backend_choice in {"http", "remote"}:
        http_backend = HTTPAgroLLMBackend(
            classify_url=config.agrollm_classify_url,
            generate_url=config.agrollm_generate_url,
            api_key=config.agrollm_api_key,
            timeout_seconds=config.agrollm_timeout_seconds,
        )
        if http_backend.available:
            return AgroLLMClient(backend=http_backend, fallback_backend=fallback)
        logger.warning("HTTP backend configured but URLs missing, using stub")
    
    # Stub backend (default)
    return AgroLLMClient(backend=fallback)
