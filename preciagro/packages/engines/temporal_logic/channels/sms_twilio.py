"""Twilio SMS channel implementation."""
import logging
from typing import Dict, Any, Optional
import aiohttp
import base64
from .base import BaseChannel, MessageResult, DeliveryStatus, ChannelConfigurationError
from ..contracts import MessageRequest
from ..config import config

logger = logging.getLogger(__name__)


class TwilioSMSChannel(BaseChannel):
    """SMS channel using Twilio API."""
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        channel_config = {
            "account_sid": config.twilio_account_sid,
            "auth_token": config.twilio_auth_token,
            "from_number": config.twilio_from_number,
            "base_url": "https://api.twilio.com/2010-04-01"
        }
        
        if config_override:
            channel_config.update(config_override)
        
        super().__init__("sms", channel_config)
        
        self.account_sid = self.config["account_sid"]
        self.auth_token = self.config["auth_token"]
        self.from_number = self.config["from_number"]
        self.base_url = self.config["base_url"]
    
    def _validate_config(self):
        """Validate Twilio SMS channel configuration."""
        required_fields = ["account_sid", "auth_token", "from_number"]
        
        for field in required_fields:
            if not self.config.get(field):
                raise ChannelConfigurationError(f"Missing required Twilio config: {field}")
        
        # Validate phone number format
        if not self.from_number.startswith("+"):
            raise ChannelConfigurationError("Twilio from_number must include country code with +")
    
    def supports_templates(self) -> bool:
        """SMS supports basic text templates."""
        return False  # Twilio SMS doesn't have templates like WhatsApp
    
    def get_template_parameters(self, template_id: str) -> Optional[Dict[str, Any]]:
        """SMS doesn't support templates."""
        return None
    
    async def send_message(self, message_request: MessageRequest) -> MessageResult:
        """Send SMS via Twilio API."""
        try:
            # Build message payload
            payload = {
                "To": self._format_phone_number(message_request.recipient),
                "From": self.from_number,
                "Body": message_request.content or "No content"
            }
            
            # Add optional parameters based on priority
            if message_request.priority >= 8:
                # High priority messages can use additional features
                payload["ValidityPeriod"] = 14400  # 4 hours validity
            
            # Send via Twilio API
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/Accounts/{self.account_sid}/Messages.json"
                
                # Basic auth header
                auth_string = f"{self.account_sid}:{self.auth_token}"
                auth_bytes = base64.b64encode(auth_string.encode()).decode()
                
                headers = {
                    "Authorization": f"Basic {auth_bytes}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                # Convert to form data
                form_data = aiohttp.FormData()
                for key, value in payload.items():
                    form_data.add_field(key, str(value))
                
                async with session.post(url, headers=headers, data=form_data) as response:
                    response_data = await response.json()
                    
                    if response.status in [200, 201]:
                        message_sid = response_data.get("sid")
                        twilio_status = response_data.get("status", "unknown")
                        
                        return MessageResult(
                            success=True,
                            message_id=message_sid,
                            status=self._map_twilio_status(twilio_status),
                            metadata={
                                "twilio_response": response_data,
                                "price": response_data.get("price"),
                                "direction": response_data.get("direction")
                            }
                        )
                    else:
                        error_msg = response_data.get("message", "Unknown error")
                        error_code = response_data.get("code", "unknown")
                        
                        return MessageResult(
                            success=False,
                            error=f"Twilio error {error_code}: {error_msg}",
                            metadata={"response": response_data}
                        )
        
        except Exception as e:
            logger.error(f"Twilio SMS send error: {e}")
            return MessageResult(
                success=False,
                error=str(e)
            )
    
    async def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get SMS delivery status from Twilio."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/Accounts/{self.account_sid}/Messages/{message_id}.json"
                
                # Basic auth header
                auth_string = f"{self.account_sid}:{self.auth_token}"
                auth_bytes = base64.b64encode(auth_string.encode()).decode()
                
                headers = {
                    "Authorization": f"Basic {auth_bytes}"
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": self._map_twilio_status(data.get("status")),
                            "error_code": data.get("error_code"),
                            "error_message": data.get("error_message"),
                            "price": data.get("price"),
                            "date_sent": data.get("date_sent"),
                            "date_updated": data.get("date_updated"),
                            "raw_response": data
                        }
                    else:
                        error_data = await response.json()
                        return {
                            "status": "unknown",
                            "error": f"API error: {error_data.get('message', response.status)}"
                        }
        
        except Exception as e:
            logger.error(f"Twilio status check error: {e}")
            return {
                "status": "unknown",
                "error": str(e)
            }
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for Twilio API."""
        # Remove spaces and ensure + prefix
        phone = phone_number.replace(" ", "").replace("-", "")
        
        if not phone.startswith("+"):
            # Assume US number if no country code
            if len(phone) == 10:
                phone = "+1" + phone
            else:
                phone = "+" + phone
        
        return phone
    
    def _map_twilio_status(self, twilio_status: str) -> str:
        """Map Twilio status to our standard status."""
        status_mapping = {
            "queued": DeliveryStatus.PENDING,
            "accepted": DeliveryStatus.PENDING,
            "sending": DeliveryStatus.PENDING,
            "sent": DeliveryStatus.SENT,
            "receiving": DeliveryStatus.SENT,
            "received": DeliveryStatus.DELIVERED,
            "delivered": DeliveryStatus.DELIVERED,
            "read": DeliveryStatus.READ,
            "undelivered": DeliveryStatus.FAILED,
            "failed": DeliveryStatus.FAILED,
            "canceled": DeliveryStatus.FAILED
        }
        return status_mapping.get(twilio_status, "unknown")
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from Twilio."""
        try:
            message_sid = webhook_data.get("MessageSid")
            message_status = webhook_data.get("MessageStatus")
            error_code = webhook_data.get("ErrorCode")
            error_message = webhook_data.get("ErrorMessage")
            
            if message_status:
                logger.info(f"Twilio SMS {message_sid} status: {message_status}")
                
                result = {
                    "processed": True,
                    "message_id": message_sid,
                    "status": message_status,
                    "mapped_status": self._map_twilio_status(message_status)
                }
                
                if error_code:
                    result.update({
                        "error_code": error_code,
                        "error_message": error_message
                    })
                
                return result
            
            # Handle incoming SMS
            if webhook_data.get("Body"):
                from_number = webhook_data.get("From")
                body = webhook_data.get("Body")
                
                logger.info(f"Received SMS from {from_number}: {body}")
                
                return {
                    "processed": True,
                    "type": "incoming_sms",
                    "sender": from_number,
                    "content": body,
                    "timestamp": webhook_data.get("DateCreated")
                }
            
            return {"processed": False, "reason": "No relevant data found"}
        
        except Exception as e:
            logger.error(f"Twilio webhook processing error: {e}")
            return {"processed": False, "error": str(e)}
    
    def get_channel_info(self) -> Dict[str, Any]:
        """Get Twilio SMS channel information."""
        base_info = super().get_channel_info()
        base_info.update({
            "account_sid": self.account_sid,
            "from_number": self.from_number,
            "capabilities": ["sms", "delivery_status", "incoming_messages"]
        })
        return base_info
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Twilio account information."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/Accounts/{self.account_sid}.json"
                
                auth_string = f"{self.account_sid}:{self.auth_token}"
                auth_bytes = base64.b64encode(auth_string.encode()).decode()
                
                headers = {
                    "Authorization": f"Basic {auth_bytes}"
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "account_sid": data.get("sid"),
                            "friendly_name": data.get("friendly_name"),
                            "status": data.get("status"),
                            "type": data.get("type"),
                            "date_created": data.get("date_created"),
                            "date_updated": data.get("date_updated")
                        }
                    else:
                        return {"error": f"Failed to get account info: {response.status}"}
        
        except Exception as e:
            logger.error(f"Error getting Twilio account info: {e}")
            return {"error": str(e)}
    
    async def send_bulk_sms(
        self, 
        recipients: list, 
        message: str, 
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """Send SMS to multiple recipients in batches."""
        results = {
            "total": len(recipients),
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        # Process in batches to avoid rate limits
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]
            
            for recipient in batch:
                try:
                    message_request = MessageRequest(
                        recipient=recipient,
                        channel="sms",
                        content=message
                    )
                    
                    result = await self.send_message(message_request)
                    
                    results["results"].append({
                        "recipient": recipient,
                        "success": result.success,
                        "message_id": result.message_id,
                        "error": result.error
                    })
                    
                    if result.success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                
                except Exception as e:
                    results["results"].append({
                        "recipient": recipient,
                        "success": False,
                        "error": str(e)
                    })
                    results["failed"] += 1
            
            # Small delay between batches
            if i + batch_size < len(recipients):
                import asyncio
                await asyncio.sleep(1)
        
        return results
