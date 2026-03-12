"""Auth helpers to enrich requests with tenant/farm/user metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status

from ..models import ChatMessageRequest, ErrorCode, ErrorDetail


@dataclass
class IdentityContext:
    """Resolved identity for a chat request."""

    tenant_id: str
    user_id: str
    farm_id: Optional[str]
    user_role: str


def resolve_identity(request: Request, payload: ChatMessageRequest) -> IdentityContext:
    """Fill missing identity fields from headers and ensure required metadata is present."""
    headers = request.headers
    tenant_id = payload.user.tenant_id or headers.get("x-tenant-id")
    user_id = payload.user.user_id or headers.get("x-user-id")
    farm_id = payload.user.farm_id or headers.get("x-farm-id")
    user_role = payload.user.role or headers.get("x-user-role") or "farmer"

    missing = []
    if not tenant_id:
        missing.append("tenant_id")
    if not user_id:
        missing.append("user_id")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "errors": [
                    ErrorDetail(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"Missing required identity fields: {', '.join(missing)}",
                        component="auth",
                    ).model_dump()
                ],
            },
        )

    payload.user.tenant_id = tenant_id
    payload.user.user_id = user_id
    payload.user.role = user_role
    if farm_id:
        payload.user.farm_id = farm_id
        if farm_id not in payload.user.farm_ids:
            payload.user.farm_ids.insert(0, farm_id)

    ctx = IdentityContext(
        tenant_id=tenant_id,
        user_id=user_id,
        farm_id=farm_id,
        user_role=user_role,
    )
    request.state.identity = ctx
    return ctx
