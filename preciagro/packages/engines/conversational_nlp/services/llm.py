"""LLM-backed response generation with safe fallbacks."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..clients.agro_llm import AgroLLMClient
from ..models import AnswerBlock, Citation, ChatMessageRequest, IntentResult


logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Constructs prompt and invokes AgroLLM, with a deterministic fallback."""

    def __init__(self, client: AgroLLMClient) -> None:
        self.client = client

    async def generate(
        self,
        request: ChatMessageRequest,
        intent: IntentResult,
        tool_outputs: Dict[str, Any],
        citations: List[Citation],
    ) -> tuple[AnswerBlock, bool]:
        prompt = self._build_prompt(request, intent, tool_outputs, citations)
        fallback_used = False

        if self.client.enabled:
            llm_text = await self.client.generate(prompt)
        else:
            llm_text = None

        if not llm_text:
            llm_text = self._fallback_text(intent, tool_outputs)
            fallback_used = True

        llm_text = self._ensure_citations(llm_text, citations)
        llm_text = self._apply_guardrails(llm_text)
        bullets = self._fallback_bullets(intent, tool_outputs)

        return AnswerBlock(text=llm_text, bullets=bullets, citations=citations), fallback_used

    @staticmethod
    def _build_prompt(
        request: ChatMessageRequest,
        intent: IntentResult,
        tool_outputs: Dict[str, Any],
        citations: List[Citation],
    ) -> str:
        """Compose a plain prompt string to feed AgroLLM."""
        parts: List[str] = []
        parts.append(
            "You are AgroAssist, a concise farm assistant. Stay truthful, avoid illegal advice, say 'I do not know' if unsure or if context is missing."
        )
        parts.append(f"User text: {request.text}")
        parts.append(f"Intent: {intent.intent}")
        parts.append(f"Entities: {intent.entities.model_dump()}")
        if tool_outputs:
            parts.append(f"Tool outputs: {tool_outputs}")
        if citations:
            parts.append(
                "Use these RAG snippets; cite their ids in-line like [zim_maize_window]. If none are helpful, say 'I do not know'. Do not invent new data."
            )
            for c in citations:
                parts.append(f"- [{c.id}] {c.snippet}")
        parts.append(
            "Safety: do not recommend illegal pesticide use or prices; if unsafe or unsure, say 'I do not know'. Respond with short steps and clear dates/numbers."
        )
        return "\n".join(parts)

    @staticmethod
    def _fallback_text(intent: IntentResult, tool_outputs: Dict[str, Any]) -> str:
        """Deterministic response if LLM is unreachable."""
        if intent.intent == "plan_planting":
            window = tool_outputs.get("temporal_logic", {}).get("recommended_window", "the next window")
            region = tool_outputs.get("geo_context", {}).get("region", "your area")
            return f"Plan to plant in {region} during {window}. Use local rainfall as the final check."
        if intent.intent == "diagnose_disease":
            diagnosis = tool_outputs.get("crop_intelligence", {}).get("diagnosis") or "Possible nutrient or disease issue detected."
            return f"I see a possible issue: {diagnosis}. Gather photos and avoid spraying until you confirm."
        if intent.intent == "inventory_status":
            return "Inventory status is unavailable; sync the inventory engine or share current stock levels."
        if intent.intent == "check_weather":
            return "Weather check stub: ensure 20-30 mm rain forecast before planting heavy seedbeds."
        return "Here is my best guidance based on current data."

    @staticmethod
    def _fallback_bullets(intent: IntentResult, tool_outputs: Dict[str, Any]) -> List[str]:
        """Build simple bullet list to complement the text."""
        bullets: List[str] = []
        if intent.intent == "plan_planting":
            recs = tool_outputs.get("crop_intelligence", {}).get("recommendations", [])
            if recs:
                bullets.extend(recs[:3])
            window = tool_outputs.get("temporal_logic", {}).get("recommended_window")
            if window:
                bullets.append(f"Target planting window: {window}.")
        elif intent.intent == "diagnose_disease":
            diagnosis = tool_outputs.get("image_analysis", {}).get("diagnosis")
            if diagnosis:
                bullets.append(f"Image analysis: {diagnosis}")
            bullets.append("Avoid spraying before confirming label and local guidance.")
        elif intent.intent == "inventory_status":
            bullets.append("Sync inventory engine to fetch live stock levels.")
        elif intent.intent == "check_weather":
            bullets.append("Check rain forecast for the next 7 days before field operations.")
        return bullets

    @staticmethod
    def _ensure_citations(text: str, citations: List[Citation]) -> str:
        """Ensure citation ids appear in text when citations are provided."""
        if not citations:
            return text
        if any(f"[{c.id}]" in text for c in citations):
            return text
        citation_str = " ".join(f"[{c.id}]" for c in citations)
        return f"{text} Citations: {citation_str}"

    @staticmethod
    def _apply_guardrails(text: str) -> str:
        """Lightweight guardrails to avoid unsafe advice."""
        unsafe_terms = ["pesticide without label", "ignore label", "illegal", "dangerous dosage"]
        lowered = text.lower()
        if any(term in lowered for term in unsafe_terms):
            return "I do not know. Please consult local guidelines and follow product labels."
        return text
