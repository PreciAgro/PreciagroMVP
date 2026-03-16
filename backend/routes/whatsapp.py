"""
POST /api/whatsapp/webhook — Twilio WhatsApp webhook handler.

Pipeline:
  Twilio POST → validate signature → classify message → process media
  → get/create farmer → assemble context → Gemini diagnosis
  → format for WhatsApp → log interaction → return TwiML
"""
import asyncio
import json
import logging
import os
import uuid

import psycopg2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from backend.core import agroai, context
from backend.core.message_classifier import classify_message
from backend.services.cloudinary_upload import upload_whatsapp_image
from backend.services.formatter import format_diagnosis
from backend.services.twilio_client import twiml_reply, validate_twilio_signature
from backend.services.whisper import transcribe_voice_note

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

_UNKNOWN_TYPE_REPLY = (
    "I can understand photos, voice notes, or text messages. "
    "Please send one of those and I'll help with your farm."
)

_VOICE_FAIL_REPLY = (
    "I couldn't understand the voice note. "
    "Can you type your question or send a photo instead?"
)

_classify = classify_message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_farmer(phone_number: str) -> str:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM farmers WHERE phone_number = %s", (phone_number,))
        row = cur.fetchone()
        if row:
            return str(row[0])
        farmer_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO farmers (id, phone_number, name, language) VALUES (%s, %s, %s, %s)",
            (farmer_id, phone_number, "Unknown", "en"),
        )
        conn.commit()
        logger.info("Auto-created farmer | phone=%s id=%s", phone_number, farmer_id)
        return farmer_id
    finally:
        cur.close()
        conn.close()


def _save_interaction(
    farmer_id: str,
    message_in: str,
    image_url: str | None,
    result: dict,
) -> None:
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO interactions
              (farmer_id, message_in, message_out, image_url, insight, action, confidence, urgency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                farmer_id,
                message_in,
                json.dumps(result),
                image_url,
                result.get("insight"),
                result.get("action"),
                result.get("confidence"),
                result.get("urgency"),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error("Interaction logging failed | farmer=%s error=%s", farmer_id, e)


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    # 1. Parse form body
    form = await request.form()
    params = dict(form)

    # 2. Validate Twilio signature
    # Railway terminates TLS and forwards as http:// internally.
    # Twilio signs against the https:// URL, so we must reconstruct it.
    signature = request.headers.get("X-Twilio-Signature", "")
    proto = request.headers.get("X-Forwarded-Proto", "https")
    url = str(request.url).replace("http://", f"{proto}://", 1)
    if not validate_twilio_signature(url, params, signature):
        logger.warning("Invalid Twilio signature | url=%s", url)
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # 3. Extract fields
    from_number: str = params.get("From", "")
    body: str = params.get("Body", "")
    num_media: int = int(params.get("NumMedia", "0"))
    media_url: str = params.get("MediaUrl0", "")
    content_type: str = params.get("MediaContentType0", "")

    msg_type = _classify(num_media, content_type, body)
    logger.info("Webhook | from=%s type=%s", from_number, msg_type)

    if msg_type == "UNKNOWN":
        return Response(content=twiml_reply(_UNKNOWN_TYPE_REPLY), media_type="application/xml")

    # 4. Look up or create farmer
    try:
        farmer_id = _get_or_create_farmer(from_number)
    except Exception as e:
        logger.error("Farmer lookup failed | phone=%s error=%s", from_number, e)
        farmer_id = from_number

    # 5. Process media
    image_url: str | None = None
    message_text: str = body.strip()

    if msg_type == "IMAGE":
        image_url = await upload_whatsapp_image(media_url, farmer_id)
        if image_url is None:
            logger.warning("Image upload failed, falling back to text-only | farmer=%s", farmer_id)
            message_text = body.strip() or "I sent a photo of my crop."

    elif msg_type == "VOICE":
        transcript = await transcribe_voice_note(media_url)
        if transcript is None:
            return Response(content=twiml_reply(_VOICE_FAIL_REPLY), media_type="application/xml")
        message_text = transcript

    # 6. Assemble context
    try:
        context_payload = await context.assemble_context(farmer_id)
    except Exception as e:
        logger.error("Context assembly failed | farmer=%s error=%s", farmer_id, e)
        context_payload = (
            f"=== FARMER CONTEXT ===\nfarmer_id: {farmer_id}\n"
            "(Context unavailable)\n=== END CONTEXT ==="
        )

    # 7. Get diagnosis
    try:
        result = await agroai.analyze(
            image_url=image_url,
            context_payload=context_payload,
            message=message_text,
            farmer_id=farmer_id,
        )
    except Exception as e:
        logger.error("AgroAI failed | farmer=%s error=%s", farmer_id, e)
        result = agroai.FALLBACK_RESPONSE

    # 8. Format and reply
    whatsapp_message = format_diagnosis(result)

    message_in = message_text if msg_type != "IMAGE" else f"[image] {body}".strip()
    asyncio.create_task(
        asyncio.get_event_loop().run_in_executor(
            None, _save_interaction, farmer_id, message_in, image_url, result
        )
    )

    return Response(content=twiml_reply(whatsapp_message), media_type="application/xml")