"""
Twilio helpers — signature validation, TwiML builder, and REST message sender.
"""
import logging
import os

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger(__name__)

EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """Return True if the X-Twilio-Signature header is valid for this request."""
    validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])
    return validator.validate(url, params, signature)


def twiml_reply(message: str) -> str:
    """Return a TwiML XML string that sends `message` back to the farmer."""
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)


def send_whatsapp_message(to: str, body: str) -> None:
    """Send a WhatsApp message via Twilio REST API (used for async replies)."""
    try:
        client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        client.messages.create(
            from_=os.environ["TWILIO_WHATSAPP_NUMBER"],
            to=to,
            body=body,
        )
        logger.info("Message sent via REST | to=%s chars=%d", to, len(body))
    except Exception as e:
        logger.error("Failed to send WhatsApp message | to=%s error=%s", to, e)
