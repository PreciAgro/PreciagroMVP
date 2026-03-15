"""
Cloudinary upload service.
Downloads an image from a Twilio media URL (requires Twilio auth),
then uploads it to Cloudinary under preciagro/farmers/{farmer_id}/.
Returns the secure_url string, or None on failure.
"""
import logging
import os

import cloudinary.uploader
import httpx

logger = logging.getLogger(__name__)


async def upload_whatsapp_image(media_url: str, farmer_id: str) -> str | None:
    """
    Download image bytes from Twilio and upload to Cloudinary.
    Retries once on Cloudinary failure.
    Returns the Cloudinary secure_url, or None if both attempts fail.
    """
    # 1. Download from Twilio — requires Basic Auth
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                media_url,
                auth=(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]),
            )
            resp.raise_for_status()
            image_bytes = resp.content
    except Exception as e:
        logger.error("Twilio media download failed | url=%s error=%s", media_url, e)
        return None

    # 2. Upload to Cloudinary (retry once)
    for attempt in range(2):
        try:
            result = cloudinary.uploader.upload(
                image_bytes,
                folder=f"preciagro/farmers/{farmer_id}",
                resource_type="image",
            )
            return result["secure_url"]
        except Exception as e:
            logger.error(
                "Cloudinary upload failed | farmer=%s attempt=%d error=%s",
                farmer_id, attempt + 1, e,
            )

    return None
