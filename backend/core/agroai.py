"""
AgroAI — single-responsibility module for Gemini API calls.
Uses google-genai SDK with API v1, inline image bytes, async-native.
"""
import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path

import httpx
from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent.parent / "docs" / "system_prompt.md"
MODEL_NAME = "gemini-2.5-flash"

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
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()

    def _try(s: str) -> dict | None:
        try:
            data = json.loads(s)
            if not REQUIRED_KEYS.issubset(data.keys()):
                return None
            data["confidence"] = float(data["confidence"])
            if data["urgency"] not in ("low", "medium", "high", "critical"):
                data["urgency"] = "low"
            return data
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    result = _try(text)
    if result:
        return result

    # Fallback: regex-extract first JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        result = _try(match.group())
        if result:
            return result

    logger.warning("Failed to parse Gemini response: %s", text[:300])
    return None


async def analyze(
    image_url: str | None,
    context_payload: str,
    message: str,
    farmer_id: str = "unknown",
) -> dict:
    """
    Calls Gemini 2.5 Flash via google-genai SDK (async, API v1beta).
    image_url is optional — pass None for text-only or voice queries.
    System prompt is prepended to the user message so it works without systemInstruction.
    """
    system_prompt = _load_system_prompt()

    # Prepend system prompt to user content (v1 doesn't support systemInstruction field)
    prompt_text = (
        f"=== SYSTEM INSTRUCTIONS ===\n{system_prompt}\n"
        f"=== END SYSTEM INSTRUCTIONS ===\n\n"
        f"{context_payload}\n\n"
        f"=== FARMER MESSAGE ===\n{message}\n\n"
        "Respond with the JSON structure only."
    )

    # Build contents list; image is optional
    contents = [prompt_text]
    if image_url:
        try:
            headers = {"User-Agent": "PreciAgro/1.0 (agricultural AI; contact@preciagro.com)"}
            async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as http:
                resp = await http.get(image_url)
                resp.raise_for_status()
                image_bytes = resp.content
                mime_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            contents.append(image_part)
        except Exception as e:
            logger.error("Image fetch failed | farmer=%s error=%s", farmer_id, e)
            return FALLBACK_RESPONSE

    client = genai.Client(
        api_key=os.environ["GOOGLE_API_KEY"],
        http_options={"api_version": "v1beta"},
    )

    config = genai_types.GenerateContentConfig(
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
                    farmer_id, attempt + 1, latency, result["confidence"], result["urgency"],
                )
                return result
            else:
                logger.warning(
                    "analyze malformed | farmer=%s attempt=%d raw=%s",
                    farmer_id, attempt + 1, raw_text[:200],
                )

        except Exception as e:
            latency = time.perf_counter() - start
            err_str = str(e)
            logger.error(
                "analyze api_error | farmer=%s attempt=%d latency=%.2fs error=%s",
                farmer_id, attempt + 1, latency, err_str,
            )
            # Don't retry on quota exhaustion — it won't help
            if "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                break
            # Brief backoff before retry on transient errors
            if attempt == 0:
                await asyncio.sleep(1)

    logger.warning("analyze fallback | farmer=%s", farmer_id)
    return FALLBACK_RESPONSE
