"""Twilio SMS channel sender."""

from twilio.rest import Client

from ..config import TWILIO_FROM, TWILIO_SID, TWILIO_TOKEN
from .base import ChannelSender


class TwilioSMSSender(ChannelSender):
    """Twilio SMS channel sender."""

    name = "sms"

    async def send(self, to, payload):
        """Send SMS via Twilio."""
        if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM):
            return {"mock": True, "status": "sent"}  # dev mode

        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            body=payload["short_text"][:1600], from_=TWILIO_FROM, to=to["phone_e164"]
        )

        return {"sid": message.sid, "status": message.status}
