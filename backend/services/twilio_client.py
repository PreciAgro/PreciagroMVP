"""
Twilio helpers — signature validation and TwiML response builder.
"""
import os

from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse


def validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """Return True if the X-Twilio-Signature header is valid for this request."""
    validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])
    return validator.validate(url, params, signature)


def twiml_reply(message: str) -> str:
    """Return a TwiML XML string that sends `message` back to the farmer."""
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)
