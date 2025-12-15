"""Response builder that composes prompts, invokes AgroLLM, and enforces guardrails."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from ..models import (
    AnswerPayload,
    ChatMessageRequest,
    Citation,
    ErrorCode,
    ErrorDetail,
    IntentResult,
    SessionContext,
    StructuredAnswer,
    ToolsContext,
    VersionManifest,
)
from .agrollm_client import AgroLLMClient

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are AgroLLM, an agronomy copilot. Combine farmer questions, tool outputs, and retrieved "
    "context to provide precise, safe, and localised guidance. Always return JSON with keys "
    "summary, steps, warnings, extras. Never invent data; cite snippets like [doc_id] when "
    "referencing retrieved context. Decline illegal or unsafe actions."
)


class ResponseBuilder:
    """Constructs prompts and parses AgroLLM outputs with deterministic fallbacks."""

    def __init__(
        self,
        client: AgroLLMClient,
        *,
        system_prompt: str | None = None,
        force_rules_mode: bool = False,
    ) -> None:
        self.client = client
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.force_rules_mode = force_rules_mode

    async def build_answer(
        self,
        *,
        request: ChatMessageRequest,
        intent: IntentResult,
        session_context: SessionContext,
        tools_context: ToolsContext,
        citations: List[Citation],
        base_errors: List[ErrorDetail],
        versions: VersionManifest,
    ) -> Tuple[AnswerPayload, bool]:
        """Return final AnswerPayload plus fallback flag."""
        errors = list(base_errors)
        fallback_used = False

        structured: StructuredAnswer | None = None
        if not self.force_rules_mode:
            structured = await self.client.generate_answer(
                request=request,
                intent=intent,
                session_context=session_context,
                tools_context=tools_context,
                rag_context=citations,
                system_prompt=self.system_prompt,
            )

        if structured is None:
            structured = self._fallback_structured(intent, tools_context)
            fallback_used = True
            errors.append(
                ErrorDetail(
                    code=ErrorCode.NLP_FALLBACK_USED,
                    message="LLM unavailable; deterministic response returned.",
                    component="response_builder",
                )
            )

        guardrail_triggered, structured = self._apply_guardrails(structured)
        if guardrail_triggered:
            fallback_used = True

        steps = structured.steps or self._fallback_steps(intent, tools_context)
        steps = self._adjust_steps_for_channel(steps, request.channel)
        summary = self._adjust_summary_for_channel(structured.summary, request.channel)
        warnings = list(structured.warnings or [])

        extras: Dict[str, Any] = dict(structured.extras or {})
        extras["session_history"] = self._history_snapshot(session_context)
        extras["tool_outputs"] = tools_context.as_dict()
        extras["rag_snippets"] = [citation.model_dump() for citation in citations]
        extras["channel"] = request.channel
        extras["feedback"] = request.feedback
        extras["locale"] = request.locale
        if request.language_preference and request.language_preference.lower() not in {"auto", ""}:
            extras["language_preference"] = request.language_preference
            warnings.append(f"Response localized stub for {request.language_preference}.")

        status_value = "ok"
        if errors or fallback_used:
            status_value = "degraded"

        answer = AnswerPayload(
            summary=summary,
            steps=steps,
            warnings=warnings,
            extras=extras,
            citations=citations,
            status=status_value,
            versions=versions,
            errors=list(errors),
        )
        return answer, fallback_used

    def _fallback_structured(
        self, intent: IntentResult, tools_context: ToolsContext
    ) -> StructuredAnswer:
        """Return deterministic structured answer when AgroLLM is unavailable."""
        summary = "Here is the best guidance based on available internal tools."
        if intent.intent == "plan_planting":
            region = tools_context.geo_context.get("region", "your area")
            window = tools_context.temporal_logic.get(
                "recommended_window", "the next suitable window"
            )
            summary = f"Plan to plant in {region} during {window}."
        elif intent.intent == "diagnose_disease":
            diagnosis = (
                tools_context.image_analysis.get("diagnosis")
                or tools_context.crop_intelligence.get("diagnosis")
                or "symptoms need more inspection."
            )
            summary = f"Preliminary diagnosis: {diagnosis}"
        elif intent.intent == "inventory_status":
            summary = "Inventory sync unavailable; confirm warehouse stock manually."
        elif intent.intent == "check_weather":
            summary = "Wait for a 20-30 mm forecast before field operations."

        steps = self._fallback_steps(intent, tools_context)
        return StructuredAnswer(
            summary=summary,
            steps=steps,
            warnings=["Validate with local regulations."],
            extras={},
        )

    def _apply_guardrails(self, answer: StructuredAnswer) -> Tuple[bool, StructuredAnswer]:
        """Detect unsafe language and provide a safe fallback when triggered."""
        unsafe_keywords = ["illegal", "banned chemical", "overdose", "ignore label", "poison"]
        text_blob = " ".join(
            [answer.summary, " ".join(answer.steps), " ".join(answer.warnings or [])]
        ).lower()
        if any(keyword in text_blob for keyword in unsafe_keywords):
            safe = StructuredAnswer(
                summary="I do not know. Consult a certified agronomist and follow product labels.",
                steps=[],
                warnings=["Unsafe guidance detected and blocked."],
                extras={},
            )
            return True, safe
        return False, answer

    def _fallback_steps(self, intent: IntentResult, tools_context: ToolsContext) -> List[str]:
        bullets: List[str] = []
        if intent.intent == "plan_planting":
            recommendations = tools_context.crop_intelligence.get("recommendations", [])
            if isinstance(recommendations, list):
                bullets.extend(str(rec) for rec in recommendations[:3])
            window = tools_context.temporal_logic.get("recommended_window")
            if window:
                bullets.append(f"Target planting window: {window}.")
        elif intent.intent == "diagnose_disease":
            diagnosis = tools_context.image_analysis.get("diagnosis")
            if diagnosis:
                bullets.append(f"Image analysis: {diagnosis}")
            bullets.append("Avoid spraying until you confirm the label and consult local experts.")
        elif intent.intent == "inventory_status":
            bullets.append("Reconcile warehouse counts and configure reorder alerts.")
        elif intent.intent == "check_weather":
            bullets.append("Check rainfall forecast for the next 7 days.")
        else:
            bullets.append("Share more data (location, crop, goal) for precise support.")
        return bullets

    @staticmethod
    def _adjust_steps_for_channel(steps: List[str], channel: str) -> List[str]:
        if channel == "mobile":
            return steps[:3]
        if channel == "chat_app":
            return [f"• {step}" for step in steps[:5]]
        return steps

    @staticmethod
    def _adjust_summary_for_channel(summary: str, channel: str) -> str:
        if channel == "mobile" and len(summary) > 200:
            return f"{summary[:197]}..."
        return summary

    @staticmethod
    def _history_snapshot(session_context: SessionContext) -> List[Dict[str, Any]]:
        turns = session_context.turns[-5:]
        return [
            {
                "role": turn.role,
                "text": turn.text[:200],
                "intent": turn.intent,
                "timestamp": turn.timestamp,
            }
            for turn in turns
        ]
