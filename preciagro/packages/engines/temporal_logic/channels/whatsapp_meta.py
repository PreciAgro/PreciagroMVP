"""WhatsApp Meta Business API channel sender."""
import httpx
import json
import os
from .base import ChannelSender
from ..config import WHATSAPP_TOKEN, WHATSAPP_PHONE_ID

class WhatsAppMetaSender(ChannelSender):
    """WhatsApp Meta Business API sender."""
    name = "whatsapp"
    
    async def send(self, to, payload):
        """Send WhatsApp message via Meta Business API."""
        if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID):
            return {"mock": True, "status": "sent"}  # dev mode
        
        url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        body = {
            "messaging_product": "whatsapp",
            "to": to["phone_e164"],
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": payload["short_text"][:1024]},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "done", "title": "DONE"}},
                        {"type": "reply", "reply": {"id": "skip", "title": "SKIP"}}
                    ]
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
        
        return r.json()
