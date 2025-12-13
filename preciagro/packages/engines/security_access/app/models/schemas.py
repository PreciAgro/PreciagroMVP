"""Pydantic schemas for Security & Access Engine API."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# Authentication Schemas
class LoginRequest(BaseModel):
    """Login request."""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str
    mfa_code: Optional[str] = None
    device_id: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response."""
    actor_id: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    requires_mfa: bool = False
    mfa_device_id: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    """Logout request."""
    revoke_all: bool = False


# Actor Schemas
class ActorCreateRequest(BaseModel):
    """Create actor request."""
    actor_type: str  # human, device, service, external
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None  # farmer, agronomist, admin, support
    full_name: Optional[str] = None
    device_name: Optional[str] = None
    device_fingerprint: Optional[str] = None
    service_name: Optional[str] = None
    service_endpoint: Optional[str] = None
    region: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ActorResponse(BaseModel):
    """Actor response."""
    actor_id: str
    actor_type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    full_name: Optional[str] = None
    device_name: Optional[str] = None
    service_name: Optional[str] = None
    trust_level: str
    region: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# MFA Schemas
class MFADeviceRegisterRequest(BaseModel):
    """Register MFA device request."""
    device_type: str = "totp"  # totp, sms, email
    device_name: Optional[str] = None


class MFADeviceRegisterResponse(BaseModel):
    """Register MFA device response."""
    device_id: str
    provisioning_uri: str
    secret: str  # For TOTP, should be shown to user once


class MFAVerifyRequest(BaseModel):
    """Verify MFA device request."""
    device_id: str
    verification_code: str


# Authorization Schemas
class PermissionCheckRequest(BaseModel):
    """Permission check request."""
    resource: str
    action: str
    context: Optional[Dict[str, Any]] = None


class PermissionCheckResponse(BaseModel):
    """Permission check response."""
    allowed: bool
    reason: Optional[str] = None


# Encryption Schemas
class EncryptRequest(BaseModel):
    """Encrypt data request."""
    data: str  # Base64 encoded
    key_id: Optional[str] = None


class EncryptResponse(BaseModel):
    """Encrypt data response."""
    encrypted_data: str  # Base64 encoded
    key_reference: str  # Format: "key_id:key_version"


class DecryptRequest(BaseModel):
    """Decrypt data request."""
    encrypted_data: str  # Base64 encoded
    key_reference: str  # Format: "key_id:key_version"


class DecryptResponse(BaseModel):
    """Decrypt data response."""
    data: str  # Base64 encoded


# Audit Schemas
class AuditLogQuery(BaseModel):
    """Audit log query parameters."""
    actor_id: Optional[str] = None
    event_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    log_id: str
    actor_id: Optional[str] = None
    event_type: str
    event_timestamp: datetime
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    success: bool
    ip_address: Optional[str] = None
    region: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# Role & Permission Schemas
class RoleCreateRequest(BaseModel):
    """Create role request."""
    role_id: str
    role_name: str
    description: Optional[str] = None
    is_system: bool = False


class PermissionCreateRequest(BaseModel):
    """Create permission request."""
    permission_id: str
    permission_name: str
    resource: str
    action: str
    description: Optional[str] = None


class RoleAssignRequest(BaseModel):
    """Assign role to actor request."""
    role_id: str


# ABAC Policy Schemas
class ABACPolicyCreateRequest(BaseModel):
    """Create ABAC policy request."""
    policy_name: str
    policy_definition: Dict[str, Any]
    description: Optional[str] = None
    priority: int = 100


class ABACPolicyResponse(BaseModel):
    """ABAC policy response."""
    policy_id: str
    policy_name: str
    description: Optional[str] = None
    policy_definition: Dict[str, Any]
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Token Verification
class TokenVerifyRequest(BaseModel):
    """Token verification request."""
    token: str


class TokenVerifyResponse(BaseModel):
    """Token verification response."""
    valid: bool
    actor_id: Optional[str] = None
    scopes: List[str] = []
    expires_at: Optional[datetime] = None
    error: Optional[str] = None

