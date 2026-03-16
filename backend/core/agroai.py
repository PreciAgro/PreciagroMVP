"""
AgroAI — single-responsibility module for Gemini API calls.
Accepts an optional image URL + assembled context, returns a structured diagnosis dict.
"""
import json
import logging
import os
import time
from pathlib import Path

import httpx
from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent.parent / "docs" / "system_prompt.md"
MODEL_NAME = "gemini-2.0-flash"

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
    """Extract and validate the JSON object from Gemini's response."""
    text = text.strip()
    # Strip markdown code fences if the model added them despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        data = json.loads(text)
        if not REQUIRED_KEYS.issubset(data.keys()):
            logger.warning("Gemini response missing required keys: %s", data.keys())
            return None
        data["confidence"] = float(data["confidence"])
        if data["urgency"] not in ("low", "medium", "high", "critical"):
            data["urgency"] = "low"
        return data
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse Gemini response: %s", e)
        return None


async def _fetch_image_bytes(image_url: str) -> tuple[bytes, str]:
    """Download image bytes and detect MIME type from Content-Type header."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        return resp.content, mime


async def analyze(
    image_url: str | None,
    context_payload: str,
    message: str,
    farmer_id: str = "unknown",
) -> dict:
    """
    Calls Gemini with the system prompt, farmer context, optional image, and message.
    Retries once on malformed JSON. Returns fallback on persistent failure.
    Logs farmer_id, latency, confidence, and urgency for every call.
    """
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    system_prompt = _load_system_prompt()

    prompt_text = (
        f"{context_payload}\n\n"
        f"=== FARMER MESSAGE ===\n{message}\n\n"
        "Please analyse the context above and respond with the JSON structure only."
    )

    contents: list = [prompt_text]

    if image_url:
        try:
            image_bytes, mime_type = await _fetch_image_bytes(image_url)
            image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            contents.append(image_part)
        except Exception as e:
            logger.error("Image fetch failed | farmer=%s url=%s error=%s", farmer_id, image_url, e)
            return FALLBACK_RESPONSE

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=1024,
        temperature=0.2,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )

    start = time.perf_counter()

    for attempt in range(2):
        try:
            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )
            raw_text = response.text
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

        except Exception as e:
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
