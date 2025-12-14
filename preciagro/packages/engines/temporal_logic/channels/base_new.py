"""Base channel interface for temporal logic engine."""

from typing import Any, Dict


class ChannelSender:
    """Base class for channel senders."""

    name = "base"

    async def send(self, to: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message through this channel.

        Args:
            to: Recipient information (e.g., {"phone_e164": "+1234567890"})
            payload: Message payload

        Returns:
            Result dictionary with status information
        """
        raise NotImplementedError
