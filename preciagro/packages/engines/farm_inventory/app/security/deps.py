"""Security dependencies for Farm Inventory Engine."""

from __future__ import annotations

from typing import List, Optional
from fastapi import Header, HTTPException, status, Depends

from ..core.config import settings


class SecurityContext:
    """Security context extracted from token/headers."""
    
    def __init__(
        self,
        engine_name: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ):
        self.engine_name = engine_name
        self.scopes = scopes or []
        self.user_id = user_id
    
    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific scope."""
        return "*" in self.scopes or scope in self.scopes
    
    def can_mutate_inventory(self) -> bool:
        """Check if context can mutate inventory (not just read)."""
        return self.has_scope("inventory:write") or self.has_scope("inventory:mutate")


async def require_service_token(
    x_preciagro_token: str | None = Header(default=None),
    x_engine_name: str | None = Header(default=None),
    x_scopes: str | None = Header(default=None),
) -> SecurityContext:
    """Service token authentication with engine scopes.
    
    Scopes:
    - inventory:read - Can read inventory
    - inventory:write - Can create/update inventory
    - inventory:mutate - Can deduct inventory (usage)
    - inventory:validate - Can validate actions
    
    Engines:
    - crop_intelligence: Can validate, read
    - temporal_logic: Can validate, deduct (scheduled tasks)
    - diagnosis_recommendation: Can validate, deduct (recommendations)
    - manual: Can do everything (farmer direct input)
    """
    expected = settings.API_AUTH_TOKEN
    if not expected:
        # Dev mode: allow without token but with limited scopes
        return SecurityContext(
            engine_name=x_engine_name or "unknown",
            scopes=["inventory:read"] if not x_preciagro_token else [],
        )
    
    if x_preciagro_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid service token",
        )
    
    # Parse scopes from header (comma-separated)
    scopes = []
    if x_scopes:
        scopes = [s.strip() for s in x_scopes.split(",")]
    
    # Default scopes based on engine
    if not scopes and x_engine_name:
        engine_scopes = {
            "crop_intelligence": ["inventory:read", "inventory:validate"],
            "temporal_logic": ["inventory:read", "inventory:validate", "inventory:mutate"],
            "diagnosis_recommendation": ["inventory:read", "inventory:validate", "inventory:mutate"],
            "manual": ["inventory:read", "inventory:write", "inventory:mutate"],
        }
        scopes = engine_scopes.get(x_engine_name, ["inventory:read"])
    
    return SecurityContext(
        engine_name=x_engine_name,
        scopes=scopes,
    )


async def require_inventory_write(
    context: SecurityContext = Depends(require_service_token),
) -> SecurityContext:
    """Require inventory write permissions."""
    if not context.can_mutate_inventory() and not context.has_scope("inventory:write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient permissions: inventory:write required",
        )
    return context

