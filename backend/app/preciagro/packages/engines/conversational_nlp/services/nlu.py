"""Intent classification and entity extraction."""

from __future__ import annotations

import logging
import re
from typing import Optional

from ..models import ChatMessageRequest, IntentEntities, IntentResult, SessionContext
from .agrollm_client import AgroLLMClient

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
    """Combines lightweight rules with the AgroLLM interface."""

    def __init__(self, client: AgroLLMClient):
        self.client = client

    async def classify(self, request: ChatMessageRequest, session: SessionContext) -> IntentResult:
        """Return intent/entities via AgroLLM with deterministic fallback."""
        llm_result = await self.client.classify_intent_and_entities(request, session)
        if llm_result:
            return llm_result
        logger.debug("AgroLLM classification unavailable, using rules fallback")
        return self._rule_based_guess(request.text, request)

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
            if re.search(rf"\b{candidate}\b", text):
                return "maize" if candidate == "corn" else candidate
        return None
