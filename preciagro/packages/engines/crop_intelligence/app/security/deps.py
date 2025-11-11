from __future__ import annotations

from fastapi import Header, HTTPException, status

from ..core.config import settings


async def require_service_token(x_preciagro_token: str | None = Header(default=None)) -> None:
    """Simple header check to gatewrite APIs when API_AUTH_TOKEN is set."""
    expected = settings.API_AUTH_TOKEN
    if not expected:
        return
    if x_preciagro_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid service token",
        )

