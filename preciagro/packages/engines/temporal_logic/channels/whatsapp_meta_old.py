"""WhatsApp Meta Business API channel implementation."""
import logging
from typing import Dict, Any, Optional
import aiohttp
import json
from .base import BaseChannel, MessageResult, DeliveryStatus, ChannelConfigurationError, MessageDeliveryError
from ..contracts import MessageRequest
from ..config import config

logger = logging.getLogger(__name__)


class WhatsAppMetaChannel(BaseChannel):
    """WhatsApp Business API channel using Meta's Cloud API."""
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        channel_config = {
            "access_token": config.whatsapp_access_token,
            "phone_number_id": config.whatsapp_phone_number_id,
            "webhook_verify_token": config.whatsapp_webhook_verify_token,
            "api_version": "v18.0",
            "base_url": "https://graph.facebook.com"
        }
        
        if config_override:
            channel_config.update(config_override)
        
        super().__init__("whatsapp", channel_config)
        
        self.access_token = self.config["access_token"]
        self.phone_number_id = self.config["phone_number_id"]
        self.api_version = self.config["api_version"]
        self.base_url = self.config["base_url"]
        
        # WhatsApp message templates
        self.message_templates = {
            "pest_alert": {
                "name": "pest_detection_alert",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "header",
                        "parameters": [{"type": "text", "text": "Pest Alert"}]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "{{pest_type}}"},
                            {"type": "text", "text": "{{location}}"},
                            {"type": "text", "text": "{{confidence}}"}
                        ]
                    }
                ]
            },
            "irrigation_reminder": {
                "name": "irrigation_reminder",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "{{soil_moisture}}"},
                            {"type": "text", "text": "{{location}}"}
                        ]
                    }
                ]
            }
        }
    
    def _validate_config(self):
        """Validate WhatsApp channel configuration."""
        required_fields = ["access_token", "phone_number_id"]
        
        for field in required_fields:
            if not self.config.get(field):
                raise ChannelConfigurationError(f"Missing required WhatsApp config: {field}")
        
        if not self.access_token.startswith(("EAA", "EAB")):
            logger.warning("WhatsApp access token format may be invalid")
    
    def supports_templates(self) -> bool:
        """WhatsApp supports message templates."""
        return True
    
    def get_template_parameters(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get parameters for a WhatsApp template."""
        if template_id in self.message_templates:
            template = self.message_templates[template_id]
            # Extract parameter names from components
            params = []
            for component in template.get("components", []):
                if component["type"] in ["header", "body", "footer"]:
                    for param in component.get("parameters", []):
                        if param["type"] == "text":
                            params.append(param["text"])
            return {"parameters": params}
        return None
    
    async def send_message(self, message_request: MessageRequest) -> MessageResult:
        """Send message via WhatsApp Business API."""
        try:
            # Build message payload
            payload = self._build_message_payload(message_request)
            
            # Send via API
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{self.api_version}/{self.phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(url, headers=headers, json=payload) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        message_id = response_data.get("messages", [{}])[0].get("id")
                        return MessageResult(
                            success=True,
                            message_id=message_id,
                            status=DeliveryStatus.SENT,
                            metadata={"whatsapp_response": response_data}
                        )
                    else:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        return MessageResult(
                            success=False,
                            error=f"WhatsApp API error: {error_msg}",
                            metadata={"response": response_data}
                        )
        
        except Exception as e:
            logger.error(f"WhatsApp message send error: {e}")
            return MessageResult(
                success=False,
                error=str(e)
            )
    
    async def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get message delivery status from WhatsApp."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{self.api_version}/{message_id}"
                headers = {
                    "Authorization": f"Bearer {self.access_token}"
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": self._map_whatsapp_status(data.get("status")),
                            "timestamp": data.get("timestamp"),
                            "raw_response": data
                        }
                    else:
                        return {
                            "status": "unknown",
                            "error": f"API error: {response.status}"
                        }
        
        except Exception as e:
            logger.error(f"WhatsApp status check error: {e}")
            return {
                "status": "unknown",
                "error": str(e)
            }
    
    def _build_message_payload(self, message_request: MessageRequest) -> Dict[str, Any]:
        """Build WhatsApp API message payload."""
        # Clean recipient (remove + if present, ensure country code)
        recipient = message_request.recipient.replace("+", "").replace(" ", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient
        }
        
        # Handle template messages
        if message_request.template_id and message_request.template_id in self.message_templates:
            template_config = self.message_templates[message_request.template_id]
            
            # Build template message
            payload.update({
                "type": "template",
                "template": {
                    "name": template_config["name"],
                    "language": template_config["language"],
                    "components": self._build_template_components(
                        template_config["components"], 
                        message_request.template_params
                    )
                }
            })
        else:
            # Simple text message
            payload.update({
                "type": "text",
                "text": {"body": message_request.content or "No content"}
            })
        
        return payload
    
    def _build_template_components(
        self, 
        components_template: list, 
        params: Dict[str, Any]
    ) -> list:
        """Build template components with parameter substitution."""
        components = []
        
        for component in components_template:
            new_component = {
                "type": component["type"]
            }
            
            if "parameters" in component:
                new_parameters = []
                for param in component["parameters"]:
                    if param["type"] == "text":
                        # Replace template placeholders
                        text_value = param["text"]
                        for key, value in params.items():
                            placeholder = f"{{{{{key}}}}}"
                            text_value = text_value.replace(placeholder, str(value))
                        
                        new_parameters.append({
                            "type": "text",
                            "text": text_value
                        })
                    else:
                        new_parameters.append(param)
                
                new_component["parameters"] = new_parameters
            
            components.append(new_component)
        
        return components
    
    def _map_whatsapp_status(self, whatsapp_status: str) -> str:
        """Map WhatsApp status to our standard status."""
        status_mapping = {
            "sent": DeliveryStatus.SENT,
            "delivered": DeliveryStatus.DELIVERED,
            "read": DeliveryStatus.READ,
            "failed": DeliveryStatus.FAILED
        }
        return status_mapping.get(whatsapp_status, "unknown")
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from WhatsApp."""
        try:
            # Extract message status updates
            if "entry" in webhook_data:
                for entry in webhook_data["entry"]:
                    if "changes" in entry:
                        for change in entry["changes"]:
                            if change.get("field") == "messages":
                                return await self._process_message_change(change["value"])
            
            return {"processed": False, "reason": "No relevant data found"}
        
        except Exception as e:
            logger.error(f"WhatsApp webhook processing error: {e}")
            return {"processed": False, "error": str(e)}
    
    async def _process_message_change(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process message status change from webhook."""
        # Handle message status updates
        if "statuses" in change_data:
            for status in change_data["statuses"]:
                message_id = status.get("id")
                status_value = status.get("status")
                timestamp = status.get("timestamp")
                
                logger.info(f"WhatsApp message {message_id} status: {status_value}")
                
                # Here you would typically update your database with the status
                # For now, just log it
                
                return {
                    "processed": True,
                    "message_id": message_id,
                    "status": status_value,
                    "timestamp": timestamp
                }
        
        # Handle incoming messages (user replies)
        if "messages" in change_data:
            for message in change_data["messages"]:
                sender = message.get("from")
                message_type = message.get("type")
                timestamp = message.get("timestamp")
                
                if message_type == "text":
                    text_body = message.get("text", {}).get("body", "")
                    logger.info(f"Received WhatsApp message from {sender}: {text_body}")
                    
                    return {
                        "processed": True,
                        "type": "incoming_message",
                        "sender": sender,
                        "content": text_body,
                        "timestamp": timestamp
                    }
        
        return {"processed": False, "reason": "No actionable data"}
    
    def verify_webhook(self, verify_token: str, mode: str, challenge: str) -> Optional[str]:
        """Verify WhatsApp webhook subscription."""
        if mode == "subscribe" and verify_token == self.config.get("webhook_verify_token"):
            logger.info("WhatsApp webhook verified successfully")
            return challenge
        
        logger.warning(f"WhatsApp webhook verification failed: mode={mode}, token_match={verify_token == self.config.get('webhook_verify_token')}")
        return None
    
    def get_channel_info(self) -> Dict[str, Any]:
        """Get WhatsApp channel information."""
        base_info = super().get_channel_info()
        base_info.update({
            "phone_number_id": self.phone_number_id,
            "api_version": self.api_version,
            "available_templates": list(self.message_templates.keys())
        })
        return base_info
