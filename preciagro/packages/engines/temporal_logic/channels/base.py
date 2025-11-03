"""Base channel interface and registry for temporal logic engine."""

from __future__ import annotations

from typing import Any, Dict


class ChannelSender:
    """Base class for channel senders."""

    name = "base"

    async def send(self, to: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message through this channel."""
        raise NotImplementedError


class ChannelManager:
    """Registry that dispatches message requests to channel implementations."""

    def __init__(self) -> None:
        self._channels: Dict[str, Any] = {}

    def register(self, channel_name: str, channel: Any) -> None:
        """Register a channel implementation."""
        self._channels[channel_name] = channel

    def get(self, channel_name: str) -> Any:
        """Return a registered channel or None."""
        return self._channels.get(channel_name)

    async def send_message(self, channel_name: str, message_request: Any) -> Any:
        """Invoke the channel's send routine with the provided request."""
        channel = self.get(channel_name)
        if channel is None:
            raise ValueError(f"Channel '{channel_name}' not registered")
        send_fn = getattr(channel, "send_message", None)
        if send_fn is None or not callable(send_fn):
            raise AttributeError(f"Channel '{channel_name}' lacks send_message()")
        return await send_fn(message_request)


channel_manager = ChannelManager()
