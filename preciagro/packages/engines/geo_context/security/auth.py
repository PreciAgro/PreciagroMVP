"""Authentication and authorization for Geo Context Engine."""

from fastapi import Header, HTTPException
from jose import jwt

from ..config import settings


def svc_auth(authorization: str = Header(None)):
    """Service authentication middleware using JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ", 1)[1]

    try:
        jwt.decode(
            token,
            settings.JWT_PUBKEY,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
