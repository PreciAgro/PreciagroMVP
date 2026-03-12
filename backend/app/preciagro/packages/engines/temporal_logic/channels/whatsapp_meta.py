"""WhatsApp Meta Business API channel sender."""

from __future__ import annotations

from typing import Any, Dict

import aiohttp


class WhatsAppChannel:
    """Minimal WhatsApp channel used in tests."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def send_message(
        self,
        message_request: Any = None,
        *,
        recipient: str | None = None,
        template: str | None = None,
        variables: Dict[str, Any] | None = None,
    ):
        """Send a templated WhatsApp message via Meta API."""
        if message_request is not None:
            recipient = getattr(message_request, "recipient", recipient)
            template = getattr(message_request, "template_id", template)
            variables = getattr(message_request, "template_params", variables)

        recipient = recipient or ""
        template = template or "default_template"
        variables = variables or {}

        url = f"https://graph.facebook.com/v20.0/{self.config['phone_number_id']}/messages"
        headers = {"Authorization": f"Bearer {self.config['access_token']}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": "en_US"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(value)} for value in variables.values()
                        ],
                    }
                ],
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.json()

        success = 200 <= response.status < 300
        message_id = data.get("messages", [{}])[0].get("id", "mock-message")
        return {
            "success": success,
            "message_id": message_id,
            "status": data.get("status", "sent"),
        }
