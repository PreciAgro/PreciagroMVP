"""Intent classification and entity extraction."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from ..clients.agro_llm import AgroLLMClient
from ..models import ChatMessageRequest, IntentEntities, IntentResult


logger = logging.getLogger(__name__)


_CROP_CANDIDATES = [
    "maize",
    "corn",
    "wheat",
    "soy",
    "soybean",
    "sorghum",
    "rice",
    "barley",
    "cotton",
    "potato",
]


class IntentClassifier:
    """Combines lightweight rules with an optional AgroLLM call."""

    def __init__(self, client: AgroLLMClient):
        self.client = client

    async def classify(self, request: ChatMessageRequest) -> IntentResult:
        """Return intent/entities using LLM when available with rule fallback."""
        rule_guess = self._rule_based_guess(request.text, request)

        if self.client.enabled:
            prompt = self._build_prompt(request)
            response = await self.client.classify(prompt)
            parsed = self._parse_llm_response(response)
            if parsed:
                return parsed

        return rule_guess

    def _rule_based_guess(self, text: str, request: ChatMessageRequest) -> IntentResult:
        lowered = text.lower()
        entities = IntentEntities()

        crop = self._extract_crop(lowered)
        if crop:
            entities.crop = crop

        metadata_location = request.metadata.get("location") or request.metadata.get("loc")
        if metadata_location:
            entities.location = str(metadata_location)

        if "urgent" in lowered or "asap" in lowered:
            entities.urgency = "high"

        intent = "general_question"
        if any(word in lowered for word in ("plant", "sow", "planting", "seed")):
            intent = "plan_planting"
        elif any(word in lowered for word in ("disease", "spot", "leaf", "symptom")):
            intent = "diagnose_disease"
        elif any(word in lowered for word in ("weather", "rain", "forecast", "rainfall")):
            intent = "check_weather"
        elif any(word in lowered for word in ("inventory", "stock", "warehouse", "input")):
            intent = "inventory_status"
        elif any(word in lowered for word in ("price", "market", "sell", "buy")):
            intent = "market_prices"

        return IntentResult(intent=intent, entities=entities, confidence=0.6)

    @staticmethod
    def _extract_crop(text: str) -> Optional[str]:
        for candidate in _CROP_CANDIDATES:
            if re.search(rf"\\b{candidate}\\b", text):
                return "maize" if candidate == "corn" else candidate
        return None

    @staticmethod
    def _build_prompt(request: ChatMessageRequest) -> str:
        """Prompt to drive AgroLLM classification."""
        examples = [
            {
                "user": "When should I plant maize in Murewa this year?",
                "intent": "plan_planting",
                "entities": {"crop": "maize", "location": "Murewa", "season_or_date": None},
            },
            {
                "user": "Leaves have yellow stripes, what is wrong?",
                "intent": "diagnose_disease",
                "entities": {"crop": None, "problem_type": "leaf symptom"},
            },
        ]
        instructions = (
            "Classify the farmer request. Respond with JSON only:\n"
            '{"intent": "<intent>", "entities": {"crop": "...", "location": "...", "field_name": null, '
            '"season_or_date": null, "problem_type": null, "urgency": "low|normal|high", "language": null}, '
            '"schema_version": "v0"}\n'
            "Constraints: return JSON only. Do not add prose. If unsure, use intent general_question and leave unknowns null."
        )
        payload = {
            "instructions": instructions,
            "examples": examples,
            "request": request.model_dump(),
        }
        return json.dumps(payload)

    @staticmethod
    def _parse_llm_response(data: Optional[dict]) -> Optional[IntentResult]:
        """Parse AgroLLM JSON output into IntentResult."""
        if not data:
            return None
        intent = data.get("intent")
        entities_raw = data.get("entities", {})
        if not intent:
            return None

        entities = IntentEntities(**entities_raw) if isinstance(entities_raw, dict) else IntentEntities()
        try:
            confidence = float(data.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        schema_version = str(data.get("schema_version", "v0"))
        return IntentResult(intent=intent, entities=entities, confidence=confidence, schema_version=schema_version)
