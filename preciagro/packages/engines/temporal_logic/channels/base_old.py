"""Base classes for communication channels."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from ..contracts import MessageRequest
from ..telemetry.metrics import engine_metrics

logger = logging.getLogger(__name__)


class ChannelError(Exception):
    """Base exception for channel errors."""

    pass


class MessageDeliveryError(ChannelError):
    """Raised when message delivery fails."""

    pass


class ChannelConfigurationError(ChannelError):
    """Raised when channel is misconfigured."""

    pass


class DeliveryStatus:
    """Message delivery status constants."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"
    REPLIED = "replied"


class MessageResult:
    """Result of a message sending operation."""

    def __init__(
        self,
        success: bool,
        message_id: Optional[str] = None,
        status: str = DeliveryStatus.PENDING,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.message_id = message_id
        self.status = status
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "message_id": self.message_id,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseChannel(ABC):
    """Abstract base class for communication channels."""

    def __init__(self, channel_name: str, config: Dict[str, Any]):
        self.channel_name = channel_name
        self.config = config
        self.enabled = config.get("enabled", True)
        self._validate_config()

    @abstractmethod
    def _validate_config(self):
        """Validate channel configuration. Raise ChannelConfigurationError if invalid."""
        pass

    @abstractmethod
    async def send_message(self, message_request: MessageRequest) -> MessageResult:
        """Send a message through this channel."""
        pass

    @abstractmethod
    async def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status for a message."""
        pass

    @abstractmethod
    def supports_templates(self) -> bool:
        """Return True if channel supports message templates."""
        pass

    @abstractmethod
    def get_template_parameters(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get parameters for a message template."""
        pass

    def is_enabled(self) -> bool:
        """Check if channel is enabled."""
        return self.enabled

    def get_channel_info(self) -> Dict[str, Any]:
        """Get channel information."""
        return {
            "name": self.channel_name,
            "enabled": self.enabled,
            "supports_templates": self.supports_templates(),
            "config_keys": list(self.config.keys()),
        }

    async def send_with_metrics(self, message_request: MessageRequest) -> MessageResult:
        """Send message with metrics tracking."""
        start_time = datetime.utcnow()

        try:
            result = await self.send_message(message_request)

            # Record metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            engine_metrics.message_sent(
                self.channel_name, result.success, duration)

            if result.success:
                logger.info(
                    f"Message sent via {self.channel_name}: {result.message_id}"
                )
            else:
                logger.warning(
                    f"Message failed via {self.channel_name}: {result.error}"
                )

            return result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            engine_metrics.message_sent(self.channel_name, False, duration)
            logger.error(f"Channel {self.channel_name} error: {e}")
            raise


class TemplateManager:
    """Manages message templates for channels."""

    def __init__(self):
        self.templates: Dict[str, Dict[str, Any]] = {}
        self._load_default_templates()

    def register_template(
        self,
        template_id: str,
        content: str,
        parameters: Optional[Dict[str, Any]] = None,
        channel_specific: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """Register a message template."""
        self.templates[template_id] = {
            "content": content,
            "parameters": parameters or {},
            "channel_specific": channel_specific or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"Registered template: {template_id}")

    def get_template(
        self, template_id: str, channel: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a message template."""
        if template_id not in self.templates:
            return None

        template = self.templates[template_id].copy()

        # Apply channel-specific overrides
        if (
            channel
            and "channel_specific" in template
            and channel in template["channel_specific"]
        ):
            channel_overrides = template["channel_specific"][channel]
            template.update(channel_overrides)

        return template

    def render_template(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        channel: Optional[str] = None,
    ) -> Optional[str]:
        """Render a template with parameters."""
        template = self.get_template(template_id, channel)
        if not template:
            return None

        content = template["content"]

        # Simple parameter substitution
        for key, value in parameters.items():
            placeholder = f"{{{key}}}"
            content = content.replace(placeholder, str(value))

        return content

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all available templates."""
        return {
            template_id: {
                "parameters": template["parameters"],
                "channels": list(template.get("channel_specific", {}).keys()),
            }
            for template_id, template in self.templates.items()
        }

    def _load_default_templates(self):
        """Load default message templates."""
        default_templates = [
            {
                "id": "pest_alert",
                "content": "🚨 Pest Alert: {pest_type} detected at {location} with {confidence}% confidence. Please inspect and take appropriate action.",
                "parameters": ["pest_type", "location", "confidence"],
            },
            {
                "id": "disease_alert",
                "content": "🦠 Disease Alert: {disease_type} detected at {location}. Severity: {severity}. Immediate attention required.",
                "parameters": ["disease_type", "location", "severity"],
            },
            {
                "id": "irrigation_reminder",
                "content": "💧 Irrigation Reminder: Soil moisture is {soil_moisture}% at {location}. Weather forecast shows {weather_condition}.",
                "parameters": ["soil_moisture", "location", "weather_condition"],
            },
            {
                "id": "weather_update",
                "content": "🌤️ Weather Update for {location}: {temperature}°C, {humidity}% humidity, {precipitation}mm rain expected.",
                "parameters": ["location", "temperature", "humidity", "precipitation"],
            },
            {
                "id": "generic_notification",
                "content": "{message}",
                "parameters": ["message"],
            },
        ]

        for template in default_templates:
            self.register_template(
                template["id"],
                template["content"],
                {param: None for param in template["parameters"]},
            )


class ChannelManager:
    """Manages all communication channels."""

    def __init__(self):
        self.channels: Dict[str, BaseChannel] = {}
        self.template_manager = TemplateManager()

    def register_channel(self, channel: BaseChannel):
        """Register a communication channel."""
        self.channels[channel.channel_name] = channel
        logger.info(f"Registered channel: {channel.channel_name}")

    def get_channel(self, channel_name: str) -> Optional[BaseChannel]:
        """Get a channel by name."""
        return self.channels.get(channel_name)

    def list_channels(self) -> Dict[str, Dict[str, Any]]:
        """List all available channels."""
        return {
            name: channel.get_channel_info() for name, channel in self.channels.items()
        }

    def get_enabled_channels(self) -> Dict[str, BaseChannel]:
        """Get all enabled channels."""
        return {
            name: channel
            for name, channel in self.channels.items()
            if channel.is_enabled()
        }

    async def send_message(
        self, channel_name: str, message_request: MessageRequest
    ) -> MessageResult:
        """Send a message through a specific channel."""
        channel = self.get_channel(channel_name)

        if not channel:
            raise ChannelError(f"Channel not found: {channel_name}")

        if not channel.is_enabled():
            raise ChannelError(f"Channel disabled: {channel_name}")

        # Handle template messages
        if message_request.template_id:
            rendered_content = self.template_manager.render_template(
                message_request.template_id,
                message_request.template_params,
                channel_name,
            )

            if rendered_content:
                # Create new request with rendered content
                message_request = MessageRequest(
                    recipient=message_request.recipient,
                    channel=message_request.channel,
                    content=rendered_content,
                    priority=message_request.priority,
                )

        return await channel.send_with_metrics(message_request)

    async def broadcast_message(
        self, message_request: MessageRequest, channels: Optional[list] = None
    ) -> Dict[str, MessageResult]:
        """Broadcast message to multiple channels."""
        if channels is None:
            channels = list(self.get_enabled_channels().keys())

        results = {}

        for channel_name in channels:
            try:
                result = await self.send_message(channel_name, message_request)
                results[channel_name] = result
            except Exception as e:
                results[channel_name] = MessageResult(
                    success=False, error=str(e))

        return results

    def health_check(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all channels."""
        health_status = {}

        for name, channel in self.channels.items():
            try:
                status = {
                    "enabled": channel.is_enabled(),
                    "healthy": True,
                    "error": None,
                }

                # You could add channel-specific health checks here

            except Exception as e:
                status = {"enabled": False, "healthy": False, "error": str(e)}

            health_status[name] = status

        return health_status


# Global channel manager instance
channel_manager = ChannelManager()
