"""Twilio SMS channel sender."""
import os
from twilio.rest import Client
from .base import ChannelSender
from ..config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER

class TwilioSMSSender(ChannelSender):
    """Twilio SMS channel sender."""
    name = "sms"
    
    async def send(self, to, payload):
        """Send SMS via Twilio."""
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
            return {"mock": True, "status": "sent"}  # dev mode
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=payload["short_text"][:1600],
            from_=TWILIO_FROM_NUMBER,
            to=to["phone_e164"]
        )
        
        return {"sid": message.sid, "status": message.status}
