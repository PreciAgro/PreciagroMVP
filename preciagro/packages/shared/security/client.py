"""Security client utilities for PreciAgro services."""
import httpx
from typing import Optional, Dict, Any
import os
from .deps import decode_token


class SecurityClient:
    """Client for interacting with security services."""

    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv(
            "SECURITY_SERVICE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("SECURITY_API_KEY")
        self.client = httpx.AsyncClient()

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate token with security service."""
        try:
            payload = decode_token(token)
            return payload
        except Exception:
            return None

    async def get_user_permissions(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get user permissions from security service."""
        # Placeholder - would make actual API call in production
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "scopes": ["geocontext:read", "geocontext:resolve"]
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_security_client: Optional[SecurityClient] = None


def get_security_client() -> SecurityClient:
    """Get or create security client instance."""
    global _security_client
    if _security_client is None:
        _security_client = SecurityClient()
    return _security_client
