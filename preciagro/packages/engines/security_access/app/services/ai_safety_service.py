"""AI safety integration service."""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from .audit_service import AuditService
from .authorization_service import AuthorizationService
from ..db.models import AuditEventType
from ..core.config import settings


class AISafetyService:
    """Service for AI safety gating and validation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)
        self.authz_service = AuthorizationService(db)
    
    async def validate_prompt(
        self,
        actor_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str], Dict[str, Any]]:
        """Validate and sanitize AI prompt.
        
        Returns:
            Tuple of (is_safe, sanitized_prompt, metadata)
        """
        metadata = {
            "original_length": len(prompt),
            "sanitized": False,
        }
        
        # Basic prompt sanitization
        sanitized = prompt
        
        # Remove potential injection patterns
        dangerous_patterns = [
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
            "eval(",
            "exec(",
        ]
        
        for pattern in dangerous_patterns:
            if pattern.lower() in sanitized.lower():
                sanitized = sanitized.replace(pattern, "")
                metadata["sanitized"] = True
        
        # Truncate if too long (prevent DoS)
        max_length = 10000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            metadata["truncated"] = True
        
        # Log prompt validation
        await self.audit_service.log_ai_event(
            actor_id,
            AuditEventType.AI_SAFETY_GATE,
            success=True,
            metadata={
                **metadata,
                "prompt_length": len(sanitized),
            },
        )
        
        return True, sanitized, metadata
    
    async def validate_output(
        self,
        actor_id: str,
        output: Dict[str, Any],
        confidence: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str], Dict[str, Any]]:
        """Validate AI output before returning to user.
        
        Returns:
            Tuple of (is_safe, error_message, metadata)
        """
        metadata = {}
        
        # Check confidence threshold
        if confidence is not None and confidence < settings.AI_CONFIDENCE_THRESHOLD:
            await self.audit_service.log_ai_event(
                actor_id,
                AuditEventType.AI_SAFETY_GATE,
                success=False,
                confidence=confidence,
                metadata={"reason": "low_confidence"},
            )
            return False, f"Confidence {confidence} below threshold {settings.AI_CONFIDENCE_THRESHOLD}", metadata
        
        # Check for unsafe content in output
        output_str = str(output)
        unsafe_patterns = [
            "malicious",
            "exploit",
            "bypass",
        ]
        
        for pattern in unsafe_patterns:
            if pattern.lower() in output_str.lower():
                await self.audit_service.log_ai_event(
                    actor_id,
                    AuditEventType.AI_SAFETY_GATE,
                    success=False,
                    confidence=confidence,
                    metadata={"reason": "unsafe_content", "pattern": pattern},
                )
                return False, f"Unsafe content detected: {pattern}", metadata
        
        # Log successful validation
        await self.audit_service.log_ai_event(
            actor_id,
            AuditEventType.AI_RECOMMENDATION,
            success=True,
            confidence=confidence,
            metadata=metadata,
        )
        
        return True, None, metadata
    
    async def check_ai_access(
        self,
        actor_id: str,
        resource_type: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if actor can access AI resources."""
        return await self.authz_service.check_permission(
            actor_id,
            resource_type,
            action,
            context or {},
        )
    
    async def gate_recommendation(
        self,
        actor_id: str,
        recommendation: Dict[str, Any],
        confidence: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Gate AI recommendation before returning to user.
        
        Returns:
            Tuple of (allowed, filtered_recommendation)
        """
        # Validate output
        is_safe, error, metadata = await self.validate_output(
            actor_id,
            recommendation,
            confidence,
            context,
        )
        
        if not is_safe:
            return False, None
        
        # Additional gating logic can be added here
        # e.g., region-specific restrictions, crop-specific rules, etc.
        
        return True, recommendation

