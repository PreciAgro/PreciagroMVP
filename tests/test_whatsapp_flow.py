"""
Tests for the WhatsApp integration pipeline.

Unit tests (no external services required):
  - Message classifier
  - Response formatter (all 4 output shapes)

Integration tests (require live credentials — skipped unless RUN_INTEGRATION=1):
  - Image path: Cloudinary upload + Gemini analysis
  - Voice path: Whisper transcription + Gemini analysis
"""
import os
import pytest

# ---------------------------------------------------------------------------
# Unit tests — message classifier
# ---------------------------------------------------------------------------

from backend.core.message_classifier import classify_message as _classify


def test_classify_image():
    assert _classify(1, "image/jpeg", "") == "IMAGE"


def test_classify_image_png():
    assert _classify(1, "image/png", "look at this") == "IMAGE"


def test_classify_voice():
    assert _classify(1, "audio/ogg", "") == "VOICE"


def test_classify_voice_with_body():
    # Body text is irrelevant when audio media is attached
    assert _classify(1, "audio/ogg; codecs=opus", "some text") == "VOICE"


def test_classify_text():
    assert _classify(0, "", "When should I apply top dressing?") == "TEXT"


def test_classify_unknown_empty_body():
    assert _classify(0, "", "") == "UNKNOWN"


def test_classify_unknown_whitespace_body():
    assert _classify(0, "", "   ") == "UNKNOWN"


# ---------------------------------------------------------------------------
# Unit tests — formatter
# ---------------------------------------------------------------------------

from backend.services.formatter import format_diagnosis

_STANDARD_DIAGNOSIS = {
    "insight": "Early signs of grey leaf spot in the upper canopy.",
    "action": "Apply mancozeb fungicide at 2g/L this afternoon.",
    "confidence": 0.87,
    "confidence_reason": "Based on image analysis + 3-day forecast.",
    "urgency": "medium",
    "follow_up": "Send another photo in 3 days to check progress.",
}

_CRITICAL_DIAGNOSIS = {
    "insight": "Severe fall armyworm infestation — 80% canopy damage.",
    "action": "Apply chlorpyrifos at 1.5 L/ha immediately.",
    "confidence": 0.91,
    "confidence_reason": "Clear larval damage pattern visible in image.",
    "urgency": "critical",
    "follow_up": "Check all fields within 500m.",
}

_LOW_CONFIDENCE_DIAGNOSIS = {
    "insight": "Leaf discolouration visible but cause is unclear.",
    "action": "Unclear — more information needed.",
    "confidence": 0.38,
    "confidence_reason": "Image resolution too low to confirm pathogen.",
    "urgency": "low",
    "follow_up": "Send a closer photo of the affected leaves.",
}


def test_format_standard_contains_insight():
    msg = format_diagnosis(_STANDARD_DIAGNOSIS)
    assert "Insight" in msg
    assert "grey leaf spot" in msg


def test_format_standard_contains_action():
    msg = format_diagnosis(_STANDARD_DIAGNOSIS)
    assert "Action" in msg
    assert "mancozeb" in msg


def test_format_standard_shows_confidence_pct():
    msg = format_diagnosis(_STANDARD_DIAGNOSIS)
    assert "87%" in msg


def test_format_standard_no_urgent_prefix():
    msg = format_diagnosis(_STANDARD_DIAGNOSIS)
    assert "URGENT" not in msg


def test_format_critical_has_urgent_prefix():
    msg = format_diagnosis(_CRITICAL_DIAGNOSIS)
    assert "URGENT" in msg


def test_format_critical_action_before_insight():
    msg = format_diagnosis(_CRITICAL_DIAGNOSIS)
    # Action should appear before Why/Insight in the critical template
    action_pos = msg.index("Action")
    insight_pos = msg.index("Why")
    assert action_pos < insight_pos


def test_format_critical_shows_confidence_pct():
    msg = format_diagnosis(_CRITICAL_DIAGNOSIS)
    assert "91%" in msg


def test_format_low_confidence_shows_observation():
    msg = format_diagnosis(_LOW_CONFIDENCE_DIAGNOSIS)
    assert "Observation" in msg


def test_format_low_confidence_shows_follow_up():
    msg = format_diagnosis(_LOW_CONFIDENCE_DIAGNOSIS)
    assert "closer photo" in msg


def test_format_low_confidence_pct():
    msg = format_diagnosis(_LOW_CONFIDENCE_DIAGNOSIS)
    assert "38%" in msg


def test_format_error_fallback_on_empty_dict():
    msg = format_diagnosis({})
    assert "couldn't process" in msg.lower()


def test_format_error_fallback_on_missing_keys():
    msg = format_diagnosis({"insight": "something"})
    assert "couldn't process" in msg.lower()


def test_format_error_fallback_on_none():
    msg = format_diagnosis(None)  # type: ignore[arg-type]
    assert "couldn't process" in msg.lower()


# ---------------------------------------------------------------------------
# Integration tests (skipped unless RUN_INTEGRATION=1)
# ---------------------------------------------------------------------------

INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"
skip_integration = pytest.mark.skipif(
    not INTEGRATION,
    reason="Set RUN_INTEGRATION=1 to run integration tests",
)


@skip_integration
def test_image_path_e2e():
    """
    Upload a real image to Cloudinary, then get a Gemini diagnosis.
    Requires: CLOUDINARY_*, GOOGLE_API_KEY, TWILIO_* env vars.
    """
    import asyncio
    from backend.services.cloudinary_upload import upload_whatsapp_image

    # Use a public test image URL that mimics a crop photo
    test_media_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Maize_plant.jpg/800px-Maize_plant.jpg"

    # For integration tests, we mock the Twilio auth by pointing at a public URL
    # (in real use, media_url is a Twilio URL requiring auth)
    import cloudinary.uploader
    import httpx

    async def _run():
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(test_media_url)
            resp.raise_for_status()
            image_bytes = resp.content
        result = cloudinary.uploader.upload(
            image_bytes,
            folder="preciagro/test",
            resource_type="image",
        )
        return result["secure_url"]

    cloudinary_url = asyncio.run(_run())
    assert cloudinary_url.startswith("https://res.cloudinary.com/")

    from backend.core import agroai
    diagnosis = asyncio.run(
        agroai.analyze(
            image_url=cloudinary_url,
            context_payload="=== FARMER CONTEXT ===\nTest farmer\n=== END CONTEXT ===",
            message="What is affecting this maize crop?",
            farmer_id="test",
        )
    )
    assert "insight" in diagnosis
    assert "action" in diagnosis
    assert isinstance(diagnosis["confidence"], float)


@skip_integration
def test_voice_path_e2e():
    """
    Download a real OGG file and transcribe via Whisper.
    Requires: OPENAI_API_KEY env var.
    """
    import asyncio
    from openai import OpenAI

    client = OpenAI()

    # Use a small public OGG file for testing
    test_ogg_url = "https://upload.wikimedia.org/wikipedia/commons/c/c8/Example.ogg"

    import httpx

    async def _download():
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.get(test_ogg_url)
            resp.raise_for_status()
            return resp.content

    audio_bytes = asyncio.run(_download())
    assert len(audio_bytes) > 0

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=("voice.ogg", audio_bytes, "audio/ogg"),
        language="en",
    )
    assert isinstance(transcript.text, str)
