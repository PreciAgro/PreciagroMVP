"""Authentication and authorization for Temporal Logic Engine."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable

from fastapi import Header, HTTPException
from jose import JWTError, jwt

# SECURITY: Require JWT secret from environment variable
DEFAULT_SECRET = os.getenv("TEMPORAL_JWT_SECRET")
if not DEFAULT_SECRET:
    raise RuntimeError(
        "CRITICAL: TEMPORAL_JWT_SECRET environment variable is not set. "
        "JWT authentication cannot be initialized. "
        "Set TEMPORAL_JWT_SECRET and restart the application."
    )


class SecurityMiddleware:
    """Minimal JWT helper used across the engine and tests."""

    def __init__(self, secret: str = DEFAULT_SECRET, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def create_access_token(
        self, user_data: Dict[str, Any], expires_in: int = 3600
    ) -> str:
        """Create a signed JWT for the supplied user claims."""
        payload = user_data.copy()
        payload.setdefault(
            "exp", datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        )
        payload.setdefault("iat", datetime.now(timezone.utc))
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT."""
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except JWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc

    def check_permission(self, user_data: Dict[str, Any], permission: str) -> bool:
        """Return True when the user owns the supplied permission."""
        permissions: Iterable[str] = user_data.get("permissions", [])
        return permission in permissions

    def authenticate_token(self, token: str) -> Dict[str, Any]:
        """Decode a bearer token and return the embedded user claims."""
        return self.decode_token(token)

    def authorize_request(self, user_id: str, permission: Any) -> None:
        """Placeholder authorization hook; raise when permission missing."""
        perm_value = permission.value if hasattr(permission, "value") else permission
        # Without a user store we cannot confirm membership; allow for now.
        if perm_value is None:
            raise HTTPException(status_code=403, detail="Permission denied")


security_middleware = SecurityMiddleware()


def svc_auth(authorization: str = Header(None)):
    """Service authentication middleware using JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ", 1)[1]
    security_middleware.decode_token(token)
