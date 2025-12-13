"""Audit logging service for security events."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AuditLog, AuditEventType, Actor
from ..core.config import settings


class AuditService:
    """Service for immutable audit logging."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _compute_event_hash(self, event_data: Dict[str, Any]) -> str:
        """Compute tamper-evident hash for an event."""
        # Create a deterministic JSON representation
        event_str = json.dumps(event_data, sort_keys=True, default=str)
        return hashlib.sha256(event_str.encode()).hexdigest()
    
    async def log_event(
        self,
        event_type: AuditEventType,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        region: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a security event."""
        event_timestamp = datetime.now(timezone.utc)
        
        # Build event data for hashing
        event_data = {
            "event_type": event_type.value,
            "actor_id": actor_id,
            "event_timestamp": event_timestamp.isoformat(),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "success": success,
            "error_message": error_message,
            "ip_address": ip_address,
            "region": region,
            "metadata": metadata or {},
        }
        
        # Compute hash
        event_hash = self._compute_event_hash(event_data)
        
        # Create audit log entry
        log_entry = AuditLog(
            log_id=f"audit_{hashlib.sha256(f'{event_timestamp.isoformat()}{actor_id or ""}{event_type.value}'.encode()).hexdigest()[:16]}",
            actor_id=actor_id,
            event_type=event_type,
            event_timestamp=event_timestamp,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            region=region,
            metadata_=metadata,
            event_hash=event_hash,
        )
        
        self.db.add(log_entry)
        await self.db.flush()
        
        return log_entry
    
    async def log_auth_event(
        self,
        event_type: AuditEventType,
        actor_id: Optional[str],
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an authentication event."""
        return await self.log_event(
            event_type=event_type,
            actor_id=actor_id,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            metadata=metadata,
        )
    
    async def log_permission_event(
        self,
        actor_id: str,
        resource_type: str,
        resource_id: Optional[str],
        action: str,
        allowed: bool,
        ip_address: Optional[str] = None,
        region: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a permission check event."""
        event_type = AuditEventType.PERMISSION_GRANTED if allowed else AuditEventType.PERMISSION_DENIED
        
        return await self.log_event(
            event_type=event_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            success=allowed,
            ip_address=ip_address,
            region=region,
            metadata=metadata,
        )
    
    async def log_data_access(
        self,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: Optional[str] = None,
        region: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log data access event."""
        event_type = {
            "read": AuditEventType.DATA_ACCESS,
            "write": AuditEventType.DATA_MODIFY,
            "delete": AuditEventType.DATA_DELETE,
        }.get(action, AuditEventType.DATA_ACCESS)
        
        return await self.log_event(
            event_type=event_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            success=True,
            ip_address=ip_address,
            region=region,
            metadata=metadata,
        )
    
    async def log_ai_event(
        self,
        actor_id: str,
        event_type: AuditEventType,
        resource_id: Optional[str] = None,
        success: bool = True,
        confidence: Optional[float] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log AI-related event."""
        ai_metadata = metadata or {}
        if confidence is not None:
            ai_metadata["confidence"] = confidence
        
        return await self.log_event(
            event_type=event_type,
            actor_id=actor_id,
            resource_type="ai_recommendation",
            resource_id=resource_id,
            success=success,
            ip_address=ip_address,
            metadata=ai_metadata,
        )
    
    async def log_admin_action(
        self,
        actor_id: str,
        action: str,
        target_resource: Optional[str] = None,
        target_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log admin action."""
        return await self.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            actor_id=actor_id,
            resource_type=target_resource,
            resource_id=target_id,
            action=action,
            success=True,
            ip_address=ip_address,
            metadata=metadata,
        )
    
    async def log_offline_sync(
        self,
        actor_id: str,
        device_id: str,
        sync_result: Dict[str, Any],
        ip_address: Optional[str] = None,
        region: Optional[str] = None,
    ) -> AuditLog:
        """Log offline sync event."""
        return await self.log_event(
            event_type=AuditEventType.OFFLINE_SYNC,
            actor_id=actor_id,
            resource_type="device",
            resource_id=device_id,
            success=sync_result.get("success", True),
            ip_address=ip_address,
            region=region,
            metadata=sync_result,
        )

