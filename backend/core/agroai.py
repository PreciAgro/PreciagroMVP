"""
AgroAI — single-responsibility module for Claude API calls.
Accepts an image URL + assembled context, returns a structured diagnosis dict.
"""
import json
import logging
import os
import time
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent.parent / "docs" / "system_prompt.md"

FALLBACK_RESPONSE = {
    "insight": "We received your photo but need a clearer image to give you accurate advice.",
    "action": "Please send another photo in good lighting, showing the affected leaves up close.",
    "confidence": 0.0,
    "confidence_reason": "Image could not be processed.",
    "urgency": "low",
    "follow_up": "What crop is affected and when did you first notice the problem?",
}

REQUIRED_KEYS = {"insight", "action", "confidence", "confidence_reason", "urgency", "follow_up"}


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _parse_response(text: str) -> dict | None:
    """Extract and validate the JSON object from Claude's response."""
    text = text.strip()
    # Strip markdown code fences if Claude added them despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        data = json.loads(text)
        if not REQUIRED_KEYS.issubset(data.keys()):
            logger.warning("Claude response missing required keys: %s", data.keys())
            return None
        # Coerce confidence to float
        data["confidence"] = float(data["confidence"])
        # Validate urgency
        if data["urgency"] not in ("low", "medium", "high", "critical"):
            data["urgency"] = "low"
        return data
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse Claude response: %s", e)
        return None


async def analyze(
    image_url: str,
    context_payload: str,
    message: str,
    farmer_id: str = "unknown",
) -> dict:
    """
    Calls Claude with the system prompt, farmer context, image, and message.
    Retries once on malformed JSON. Returns fallback on persistent failure.
    Logs farmer_id, latency, confidence, and urgency for every call.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system_prompt = _load_system_prompt()

    user_content = [
        {
            "type": "text",
            "text": (
                f"{context_payload}\n\n"
                f"=== FARMER MESSAGE ===\n{message}\n\n"
                "Please analyse the image and the context above and respond with the JSON structure only."
            ),
        },
        {
            "type": "image",
            "source": {
                "type": "url",
                "url": image_url,
            },
        },
    ]

    start = time.perf_counter()

    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            raw_text = response.content[0].text
            result = _parse_response(raw_text)

            latency = time.perf_counter() - start
            if result:
                logger.info(
                    "analyze ok | farmer=%s attempt=%d latency=%.2fs confidence=%.2f urgency=%s",
                    farmer_id,
                    attempt + 1,
                    latency,
                    result["confidence"],
                    result["urgency"],
                )
                return result
            else:
                logger.warning(
                    "analyze malformed | farmer=%s attempt=%d raw=%s",
                    farmer_id,
                    attempt + 1,
                    raw_text[:200],
                )

        except anthropic.APIError as e:
            latency = time.perf_counter() - start
            logger.error(
                "analyze api_error | farmer=%s attempt=%d latency=%.2fs error=%s",
                farmer_id,
                attempt + 1,
                latency,
                str(e),
            )
            break

    logger.warning("analyze fallback | farmer=%s", farmer_id)
    return FALLBACK_RESPONSE
