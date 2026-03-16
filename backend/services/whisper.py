"""
Whisper transcription service.
Downloads a voice note from a Twilio media URL (requires Twilio auth),
then transcribes it via OpenAI Whisper.
WhatsApp voice notes arrive as audio/ogg (Opus) — Whisper accepts this directly.
Returns the transcript string, or None on failure/timeout.
"""
import asyncio
import logging
import os

import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)


async def transcribe_voice_note(media_url: str) -> str | None:
    """
    Download OGG audio from Twilio and transcribe via Whisper.
    Returns transcript text, or None if download or transcription fails.
    Applies a 15-second timeout to the transcription call.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                media_url,
                auth=(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]),
            )
            resp.raise_for_status()
            audio_bytes = resp.content
    except Exception as e:
        logger.error("Twilio audio download failed | url=%s error=%s", media_url, e)
        return None

    openai_client = OpenAI()
    try:
        transcript = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("voice.ogg", audio_bytes, "audio/ogg"),
                    language="en",
                ),
            ),
            timeout=15.0,
        )
        text = transcript.text.strip()
        if not text:
            logger.warning("Whisper returned empty transcript | url=%s", media_url)
            return None
        return text
    except asyncio.TimeoutError:
        logger.error("Whisper transcription timed out | url=%s", media_url)
        return None
    except Exception as e:
        logger.error("Whisper transcription failed | url=%s error=%s", media_url, e)
        return None
