"""API routes for Security & Access Engine."""

import base64
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..models.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutRequest,
    ActorCreateRequest,
    ActorResponse,
    MFADeviceRegisterRequest,
    MFADeviceRegisterResponse,
    MFAVerifyRequest,
    PermissionCheckRequest,
    PermissionCheckResponse,
    EncryptRequest,
    EncryptResponse,
    DecryptRequest,
    DecryptResponse,
    AuditLogQuery,
    AuditLogResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
    RoleCreateRequest,
    PermissionCreateRequest,
    RoleAssignRequest,
    ABACPolicyCreateRequest,
    ABACPolicyResponse,
)
from ..services.auth_service import AuthenticationService
from ..services.identity_service import IdentityService
from ..services.authorization_service import AuthorizationService
from ..services.encryption_service import EncryptionService
from ..services.audit_service import AuditService
from ..services.token_service import TokenService
from ..db.models import ActorType, HumanRole, AuditEventType
from ..core.config import settings

router = APIRouter(prefix="/v1", tags=["security"])


# Helper to get client IP
def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# Authentication Endpoints
@router.post("/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email/phone and password."""
    auth_service = AuthenticationService(db)

    actor, access_token, refresh_token, requires_mfa = (
        await auth_service.authenticate_with_password(
            email=request.email,
            phone=request.phone,
            password=request.password,
            ip_address=get_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent"),
        )
    )

    if not actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if requires_mfa:
        # If MFA code provided, verify it
        if request.mfa_code:
            access_token, refresh_token, verified = await auth_service.verify_mfa(
                actor.actor_id,
                request.mfa_code,
                request.device_id,
                get_client_ip(http_request),
                http_request.headers.get("User-Agent"),
            )
            if not verified:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code",
                )
            requires_mfa = False
        else:
            # Return MFA required response
            return LoginResponse(
                actor_id=actor.actor_id,
                access_token="",
                refresh_token="",
                expires_in=0,
                requires_mfa=True,
            )

    return LoginResponse(
        actor_id=actor.actor_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        requires_mfa=False,
    )


@router.post("/auth/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token."""
    auth_service = AuthenticationService(db)

    access_token, refresh_token, success = await auth_service.refresh_access_token(
        request.refresh_token,
        get_client_ip(http_request),
        http_request.headers.get("User-Agent"),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/auth/logout")
async def logout(
    request: LogoutRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
):
    """Logout and revoke tokens."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = authorization.split(" ", 1)[1]
    auth_service = AuthenticationService(db)

    success = await auth_service.logout(token, request.revoke_all, get_client_ip(http_request))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return {"message": "Logged out successfully"}


@router.post("/auth/verify", response_model=TokenVerifyResponse)
async def verify_token(
    request: TokenVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify a token."""
    token_service = TokenService(db)
    payload = await token_service.verify_token(request.token)

    if not payload:
        return TokenVerifyResponse(valid=False, error="Invalid or expired token")

    expires_at = datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)

    return TokenVerifyResponse(
        valid=True,
        actor_id=payload.get("sub"),
        scopes=payload.get("scopes", []),
        expires_at=expires_at,
    )


# MFA Endpoints
@router.post("/auth/mfa/register", response_model=MFADeviceRegisterResponse)
async def register_mfa_device(
    request: MFADeviceRegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
):
    """Register a new MFA device."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = authorization.split(" ", 1)[1]
    token_service = TokenService(db)
    payload = await token_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    actor_id = payload.get("sub")
    auth_service = AuthenticationService(db)

    device_id, provisioning_uri = await auth_service.register_mfa_device(
        actor_id,
        request.device_type,
        request.device_name,
    )

    # Extract secret from provisioning URI (for TOTP)
    secret = (
        provisioning_uri.split("secret=")[1].split("&")[0] if "secret=" in provisioning_uri else ""
    )

    return MFADeviceRegisterResponse(
        device_id=device_id,
        provisioning_uri=provisioning_uri,
        secret=secret,
    )


@router.post("/auth/mfa/verify")
async def verify_mfa_device(
    request: MFAVerifyRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
):
    """Verify an MFA device."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = authorization.split(" ", 1)[1]
    token_service = TokenService(db)
    payload = await token_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    actor_id = payload.get("sub")
    auth_service = AuthenticationService(db)

    success = await auth_service.verify_mfa_device(
        actor_id,
        request.device_id,
        request.verification_code,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    return {"message": "MFA device verified successfully"}


# Actor Management
@router.post("/actors", response_model=ActorResponse)
async def create_actor(
    request: ActorCreateRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new actor."""
    identity_service = IdentityService(db)
    password_service = PasswordService()

    # Hash password if provided
    password_hash = None
    if request.password:
        password_hash = password_service.hash_password(request.password)

    # Convert string to enum
    actor_type = ActorType(request.actor_type)
    role = HumanRole(request.role) if request.role else None

    actor = await identity_service.create_actor(
        actor_type=actor_type,
        email=request.email,
        phone=request.phone,
        password_hash=password_hash,
        role=role,
        full_name=request.full_name,
        device_name=request.device_name,
        device_fingerprint=request.device_fingerprint,
        service_name=request.service_name,
        service_endpoint=request.service_endpoint,
        region=request.region,
        capabilities=request.capabilities,
        metadata=request.metadata,
    )

    await db.commit()

    return ActorResponse.model_validate(actor)


@router.get("/actors/{actor_id}", response_model=ActorResponse)
async def get_actor(
    actor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get actor by ID."""
    identity_service = IdentityService(db)
    actor = await identity_service.get_actor_by_id(actor_id)

    if not actor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actor not found",
        )

    return ActorResponse.model_validate(actor)


# Authorization
@router.post("/authorize/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
):
    """Check if actor has permission."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = authorization.split(" ", 1)[1]
    token_service = TokenService(db)
    payload = await token_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    actor_id = payload.get("sub")
    authz_service = AuthorizationService(db)
    audit_service = AuditService(db)

    # Add request context
    context = request.context or {}
    context["ip_address"] = get_client_ip(http_request)
    context["user_agent"] = http_request.headers.get("User-Agent")

    allowed = await authz_service.check_permission(
        actor_id,
        request.resource,
        request.action,
        context,
    )

    # Log permission check
    await audit_service.log_permission_event(
        actor_id,
        request.resource,
        None,
        request.action,
        allowed,
        get_client_ip(http_request),
        metadata=context,
    )

    return PermissionCheckResponse(
        allowed=allowed,
        reason=None if allowed else "Permission denied",
    )


# Encryption
@router.post("/encrypt", response_model=EncryptResponse)
async def encrypt_data(
    request: EncryptRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
):
    """Encrypt data."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = authorization.split(" ", 1)[1]
    token_service = TokenService(db)
    payload = await token_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    encryption_service = EncryptionService(db)

    # Decode base64 data
    data_bytes = base64.b64decode(request.data)

    # Encrypt
    encrypted_data, key_reference = await encryption_service.encrypt_data(
        data_bytes,
        request.key_id,
    )

    # Encode result
    encrypted_b64 = base64.b64encode(encrypted_data).decode()

    return EncryptResponse(
        encrypted_data=encrypted_b64,
        key_reference=key_reference,
    )


@router.post("/decrypt", response_model=DecryptResponse)
async def decrypt_data(
    request: DecryptRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
):
    """Decrypt data."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = authorization.split(" ", 1)[1]
    token_service = TokenService(db)
    payload = await token_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    encryption_service = EncryptionService(db)

    # Decode base64 data
    encrypted_bytes = base64.b64decode(request.encrypted_data)

    # Decrypt
    decrypted_data = await encryption_service.decrypt_data(
        encrypted_bytes,
        request.key_reference,
    )

    # Encode result
    decrypted_b64 = base64.b64encode(decrypted_data).decode()

    return DecryptResponse(data=decrypted_b64)


# Audit Logs
@router.get("/audit/logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    query: AuditLogQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
):
    """Get audit logs."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # TODO: Implement audit log query
    # This is a placeholder - implement proper querying
    return []


# Health Check
@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "engine": "security_access"}
