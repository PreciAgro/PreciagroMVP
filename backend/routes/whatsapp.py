"""
POST /api/whatsapp/webhook — Twilio WhatsApp webhook handler.

Pattern: return empty TwiML immediately (avoids Twilio 15s timeout),
then process the message in a background task and reply via REST API.
"""
import asyncio
import json
import logging
import os
import uuid

import psycopg2
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import Response

from backend.core import agroai, context
from backend.core.message_classifier import classify_message
from backend.services.cloudinary_upload import upload_whatsapp_image
from backend.services.formatter import format_diagnosis
from backend.services.twilio_client import (
    EMPTY_TWIML,
    send_whatsapp_message,
    validate_twilio_signature,
)
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
# Background pipeline — runs after we've already returned 200 to Twilio
# ---------------------------------------------------------------------------

async def _process_and_reply(
    from_number: str,
    body: str,
    num_media: int,
    media_url: str,
    content_type: str,
) -> None:
    msg_type = classify_message(num_media, content_type, body)
    logger.info("Processing | from=%s type=%s", from_number, msg_type)

    if msg_type == "UNKNOWN":
        send_whatsapp_message(from_number, _UNKNOWN_TYPE_REPLY)
        return

    # Farmer lookup
    try:
        farmer_id = _get_or_create_farmer(from_number)
    except Exception as e:
        logger.error("Farmer lookup failed | phone=%s error=%s", from_number, e)
        farmer_id = from_number

    # Media processing
    image_url: str | None = None
    message_text: str = body.strip()

    if msg_type == "IMAGE":
        image_url = await upload_whatsapp_image(media_url, farmer_id)
        if image_url is None:
            logger.warning("Image upload failed, text-only | farmer=%s", farmer_id)
            message_text = body.strip() or "I sent a photo of my crop."

    elif msg_type == "VOICE":
        transcript = await transcribe_voice_note(media_url)
        if transcript is None:
            send_whatsapp_message(from_number, _VOICE_FAIL_REPLY)
            return
        message_text = transcript

    # Context assembly
    try:
        context_payload = await context.assemble_context(farmer_id)
    except Exception as e:
        logger.error("Context assembly failed | farmer=%s error=%s", farmer_id, e)
        context_payload = (
            f"=== FARMER CONTEXT ===\nfarmer_id: {farmer_id}\n"
            "(Context unavailable)\n=== END CONTEXT ==="
        )

    # Gemini diagnosis
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

    # Send reply via REST (not TwiML — we already returned empty TwiML)
    whatsapp_message = format_diagnosis(result)
    send_whatsapp_message(from_number, whatsapp_message)

    # Log interaction (non-blocking)
    message_in = message_text if msg_type != "IMAGE" else f"[image] {body}".strip()
    asyncio.get_event_loop().run_in_executor(
        None, _save_interaction, farmer_id, message_in, image_url, result
    )


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    # 1. Parse form body
    form = await request.form()
    params = dict(form)

    # 2. Validate Twilio signature
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

    # 4. Queue processing as background task and return immediately
    # This avoids Twilio's 15-second webhook timeout for slow Gemini calls.
    background_tasks.add_task(
        _process_and_reply, from_number, body, num_media, media_url, content_type
    )

    return Response(content=EMPTY_TWIML, media_type="application/xml")
