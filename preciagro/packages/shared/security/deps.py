"""Security dependencies for PreciAgro services."""
from fastapi import Depends, HTTPException, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import List, Optional
import os
from functools import wraps


# JWT Configuration
JWT_PUBKEY = os.getenv("JWT_PUBKEY", "")
ALGORITHM = "RS256"
# Allow dev mode to bypass JWT validation if key is missing
DEV_MODE = os.getenv("DEV_MODE", os.getenv("DEBUG", "false")).lower() == "true"

# Security scheme
security = HTTPBearer()


class TenantContext:
    """Tenant context information extracted from JWT token."""

    def __init__(self, tenant_id: str, user_id: str, scopes: List[str]):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.scopes = scopes


def decode_token(token: str) -> dict:
    """Decode and validate JWT token.

    In dev mode with no JWT_PUBKEY configured, returns a stub context.
    In production, missing JWT_PUBKEY results in 401 Unauthorized.
    """
    if not JWT_PUBKEY:
        if DEV_MODE:
            # Dev mode bypass: return a stub context without validation
            return {
                "tenant_id": "dev-tenant",
                "user_id": "dev-user",
                "scopes": ["*"],
                "sub": "dev-user"
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication required: JWT_PUBKEY not configured"
            )

    try:
        payload = jwt.decode(
            token,
            JWT_PUBKEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )


def get_tenant_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(
        security, scopes=[])
) -> TenantContext:
    """Extract tenant context from JWT token.

    In dev mode with no credentials, returns a stub context.
    In production, authentication is required.
    """
    if not credentials:
        if DEV_MODE:
            # Dev mode bypass
            return TenantContext(
                tenant_id="dev-tenant",
                user_id="dev-user",
                scopes=["*"]
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )

    payload = decode_token(credentials.credentials)

    tenant_id = payload.get("tenant_id", payload.get("sub", "unknown"))
    user_id = payload.get("user_id", payload.get("sub", "unknown"))
    scopes = payload.get("scopes", payload.get("scope", "").split())

    return TenantContext(tenant_id, user_id, scopes)


def require_scopes(*required_scopes: str):
    """Dependency factory for requiring specific scopes."""

    def scope_dependency(
        tenant_ctx: TenantContext = Depends(get_tenant_context)
    ) -> TenantContext:
        """Check if user has required scopes."""
        if not required_scopes:
            return tenant_ctx

        user_scopes = set(tenant_ctx.scopes)
        required_scopes_set = set(required_scopes)

        if not required_scopes_set.issubset(user_scopes):
            missing_scopes = required_scopes_set - user_scopes
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Missing scopes: {', '.join(missing_scopes)}"
            )

        return tenant_ctx

    return scope_dependency


# Alias for backward compatibility
tenant_ctx = get_tenant_context


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """Basic authentication requirement - just validate token."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return decode_token(credentials.credentials)


# Input validation helpers
def validate_polygon_size(coordinates: List, max_vertices: int = 500, max_area_ha: float = 5000.0):
    """Validate polygon size constraints."""
    if not coordinates or not coordinates[0]:
        raise HTTPException(
            status_code=400, detail="Invalid polygon coordinates")

    # Check vertex count
    vertex_count = len(coordinates[0])
    if vertex_count > max_vertices:
        raise HTTPException(
            status_code=400,
            detail=f"Polygon has too many vertices: {vertex_count} > {max_vertices}"
        )

    # Rough area calculation (simplified)
    # In production, would use proper spherical area calculation
    if len(coordinates[0]) >= 3:
        # Simple bounding box area estimate
        lons = [coord[0] for coord in coordinates[0]]
        lats = [coord[1] for coord in coordinates[0]]

        lon_range = max(lons) - min(lons)
        lat_range = max(lats) - min(lats)

        # Very rough area estimate in hectares (111 km per degree at equator)
        estimated_area_ha = lon_range * lat_range * \
            111 * 111 * 100  # Convert to hectares

        if estimated_area_ha > max_area_ha:
            raise HTTPException(
                status_code=400,
                detail=f"Polygon area too large: ~{estimated_area_ha:.0f} ha > {max_area_ha} ha"
            )


def sanitize_for_logs(data: dict) -> dict:
    """Remove sensitive data from logs."""
    sanitized = data.copy()

    # Remove raw geometry to avoid log bloat
    if "field" in sanitized and isinstance(sanitized["field"], dict):
        if "coordinates" in sanitized["field"]:
            coord_count = len(
                sanitized["field"]["coordinates"][0]) if sanitized["field"]["coordinates"] else 0
            sanitized["field"] = {
                "type": sanitized["field"].get("type", "unknown"),
                "vertex_count": coord_count
            }

    # Remove other potentially large fields
    for field in ["polygon", "geometry"]:
        if field in sanitized:
            sanitized[field] = f"<{field}_redacted>"

    return sanitized
