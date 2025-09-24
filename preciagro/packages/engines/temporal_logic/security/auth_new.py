"""Authentication and authorization for Temporal Logic Engine."""
from fastapi import Depends, HTTPException, Header
from jose import jwt
from ..config import JWT_PUBKEY


def svc_auth(authorization: str = Header(None)):
    """Service authentication middleware using JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ", 1)[1]

    try:
        jwt.decode(token, JWT_PUBKEY, algorithms=[
                   "RS256"], options={"verify_aud": False})
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
