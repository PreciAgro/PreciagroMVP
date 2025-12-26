"""Minimal Twilio SMS channel used for unit tests."""

from __future__ import annotations

from typing import Any, Dict

import aiohttp


class SMSChannel:
    """Thin Twilio SMS wrapper that mirrors the test expectations."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def send_message(
        self,
        message_request: Any = None,
        *,
        recipient: str | None = None,
        message: str | None = None,
    ) -> Dict[str, Any]:
        """Send an SMS via the Twilio REST API."""
        if message_request is not None:
            recipient = getattr(message_request, "recipient", recipient)
            message = getattr(message_request, "content", message)

        recipient = recipient or ""
        message = message or ""

        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.config['account_sid']}/Messages.json"
        )
        payload = {
            "To": recipient,
            "From": self.config["from_number"],
            "Body": message,
        }

        auth = aiohttp.BasicAuth(self.config["account_sid"], self.config["auth_token"])

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, auth=auth) as response:
                data = await response.json()

        success = 200 <= response.status < 300
        message_id = data.get("sid", "mock-sid")
        return {
            "success": success,
            "message_id": message_id,
            "status": data.get("status", "queued"),
        }
