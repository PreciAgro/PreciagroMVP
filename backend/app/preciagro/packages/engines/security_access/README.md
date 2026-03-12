# 🔐 PreciAgro Security & Access Engine

Enterprise-grade Security & Access Engine for PreciAgro, providing identity, authentication, authorization, encryption, and audit capabilities.

## Overview

The Security & Access Engine is the **foundational security layer** for PreciAgro. It enforces trust across the entire platform, protecting farmer data, farm information, images, geo data, and inventory while controlling access through a comprehensive RBAC + ABAC authorization model.

## Architecture

### Core Components

1. **Identity Service** - Actor-based identity management (Human, Device, Service, External)
2. **Authentication Service** - Password, OTP, MFA, device certificates, mTLS
3. **Authorization Service** - RBAC + ABAC policy engine
4. **Encryption Service** - Envelope encryption with key management
5. **Audit Service** - Immutable audit logging
6. **AI Safety Service** - AI output validation and gating

### Key Features

- ✅ **Actor-Based Identity Model** - Supports Human, Device, Service, External actors
- ✅ **Multi-Factor Authentication** - TOTP, SMS OTP support
- ✅ **Short-Lived Tokens** - 15-minute access tokens with refresh rotation
- ✅ **RBAC + ABAC** - Role-based and attribute-based access control
- ✅ **Envelope Encryption** - AES-256-GCM with automatic key rotation
- ✅ **Immutable Audit Logs** - Tamper-evident event logging
- ✅ **AI Safety Integration** - Prompt sanitization and output validation
- ✅ **Offline/Edge Security** - Trust degradation and sync revalidation
- ✅ **Compliance-Ready** - GDPR, data residency, consent tracking hooks

## Database Schema

### Core Tables

- `security_actors` - Actor identities
- `security_roles` - RBAC roles
- `security_permissions` - Permissions (resource:action)
- `security_role_permissions` - Role-permission mapping
- `security_actor_roles` - Actor-role assignments
- `security_tokens` - Authentication tokens
- `security_mfa_devices` - MFA device registrations
- `security_encryption_keys` - Encryption key management
- `security_audit_logs` - Immutable audit trail
- `security_abac_policies` - ABAC policy definitions

## API Endpoints

### Authentication

- `POST /v1/auth/login` - Authenticate with email/phone + password
- `POST /v1/auth/refresh` - Refresh access token
- `POST /v1/auth/logout` - Logout and revoke tokens
- `POST /v1/auth/verify` - Verify token validity
- `POST /v1/auth/mfa/register` - Register MFA device
- `POST /v1/auth/mfa/verify` - Verify MFA device

### Identity Management

- `POST /v1/actors` - Create new actor
- `GET /v1/actors/{actor_id}` - Get actor details

### Authorization

- `POST /v1/authorize/check` - Check permission

### Encryption

- `POST /v1/encrypt` - Encrypt data
- `POST /v1/decrypt` - Decrypt data

### Audit

- `GET /v1/audit/logs` - Query audit logs

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/preciagro

# JWT
JWT_ALGORITHM=RS256  # or HS256 for dev
JWT_PRIVATE_KEY=<RSA private key>
JWT_PUBLIC_KEY=<RSA public key>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Hashing
PASSWORD_HASH_ALGORITHM=argon2id  # or bcrypt
ARGON2_TIME_COST=2
ARGON2_MEMORY_COST=65536

# Encryption
ENCRYPTION_MASTER_KEY=<32-byte master key>
ENCRYPTION_ALGORITHM=AES-256-GCM
KEY_ROTATION_INTERVAL_DAYS=90

# MFA
MFA_ISSUER_NAME=PreciAgro
TOTP_VALIDITY_WINDOW=1

# Feature Flags
DEV_MODE=false
AUDIT_LOG_ENABLED=true
AI_SAFETY_ENABLED=true
```

## Usage Examples

### 1. Create a Farmer Actor

```python
from preciagro.packages.engines.security_access.app.services.identity_service import IdentityService
from preciagro.packages.engines.security_access.app.services.password_service import PasswordService
from preciagro.packages.engines.security_access.app.db.models import ActorType, HumanRole

identity_service = IdentityService(db)
password_service = PasswordService()

password_hash = password_service.hash_password("secure_password")

actor = await identity_service.create_actor(
    actor_type=ActorType.HUMAN,
    email="farmer@example.com",
    phone="+1234567890",
    password_hash=password_hash,
    role=HumanRole.FARMER,
    full_name="John Farmer",
    region="EU",
)
```

### 2. Authenticate

```python
from preciagro.packages.engines.security_access.app.services.auth_service import AuthenticationService

auth_service = AuthenticationService(db)

actor, access_token, refresh_token, requires_mfa = await auth_service.authenticate_with_password(
    email="farmer@example.com",
    password="secure_password",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
)
```

### 3. Check Permission

```python
from preciagro.packages.engines.security_access.app.services.authorization_service import AuthorizationService

authz_service = AuthorizationService(db)

allowed = await authz_service.check_permission(
    actor_id="actor_123",
    resource="farm",
    action="read",
    context={
        "region": "EU",
        "crop_type": "maize",
    },
)
```

### 4. Encrypt Data

```python
from preciagro.packages.engines.security_access.app.services.encryption_service import EncryptionService

encryption_service = EncryptionService(db)

encrypted_data, key_reference = await encryption_service.encrypt_data(
    data=b"sensitive data",
    key_id="default",
)
```

### 5. ABAC Policy Example

```python
from preciagro.packages.engines.security_access.app.services.authorization_service import AuthorizationService

authz_service = AuthorizationService(db)

policy = await authz_service.create_abac_policy(
    policy_name="EU Farmers Read Own Farms",
    policy_definition={
        "subject": {
            "role": "farmer",
            "region": "EU",
        },
        "resource": {
            "type": "farm",
        },
        "action": "read",
        "conditions": {
            "region": {"$in": ["EU", "PL"]},
        },
        "effect": "allow",
    },
    priority=100,
)
```

## API Gateway Integration

The Security Engine provides middleware for API Gateway integration:

```python
from preciagro.packages.engines.security_access.app.middleware.gateway_integration import SecurityGatewayMiddleware

app.add_middleware(SecurityGatewayMiddleware)
```

This middleware:
- Validates authentication tokens
- Performs authorization checks
- Logs security events
- Adds security context to requests

## AI Safety Integration

The engine provides hooks for AI safety:

```python
from preciagro.packages.engines.security_access.app.services.ai_safety_service import AISafetyService

ai_safety = AISafetyService(db)

# Validate prompt
is_safe, sanitized_prompt, metadata = await ai_safety.validate_prompt(
    actor_id="actor_123",
    prompt=user_prompt,
)

# Gate recommendation
allowed, filtered_rec = await ai_safety.gate_recommendation(
    actor_id="actor_123",
    recommendation=ai_output,
    confidence=0.85,
)
```

## Offline/Edge Security

For offline scenarios:

1. **Trust Degradation**: Trust level decreases after being offline for X hours
2. **Signed Actions**: All offline actions are cryptographically signed
3. **Sync Revalidation**: Server-side revalidation on sync

## Compliance Features

- **GDPR Ready**: Consent tracking, data deletion, export hooks
- **Data Residency**: Region-based data storage policies
- **Audit Trail**: Immutable logs for compliance audits

## Security Best Practices

1. **Zero Trust**: Every request is authenticated and authorized
2. **Least Privilege**: Actors only get minimum required permissions
3. **Short-Lived Credentials**: Access tokens expire in 15 minutes
4. **Token Rotation**: Refresh tokens rotate on use
5. **Encryption Everywhere**: Data at rest and in transit encrypted
6. **Audit Everything**: All security events logged immutably

## Running the Engine

```bash
# Set environment variables
export DATABASE_URL=postgresql+asyncpg://...
export JWT_PRIVATE_KEY=...
export ENCRYPTION_MASTER_KEY=...

# Run migrations
alembic upgrade head

# Start server
uvicorn preciagro.packages.engines.security_access.app.main:app --port 8105
```

## Testing

```bash
# Run tests
pytest preciagro/packages/engines/security_access/tests/
```

## Production Deployment

1. **Generate RSA keys** for JWT signing
2. **Set strong master key** for encryption (32 bytes)
3. **Configure KMS** (AWS KMS, Azure Key Vault, etc.)
4. **Enable audit logging** with retention policies
5. **Set up monitoring** for security events
6. **Configure rate limiting** to prevent abuse
7. **Enable MFA** for admin accounts

## Future Enhancements

- [ ] Device certificate management
- [ ] ] mTLS for service-to-service communication
- [ ] OAuth2/OIDC integration
- [ ] SAML support
- [ ] Biometric authentication
- [ ] Hardware security modules (HSM) integration
- [ ] Advanced threat detection
- [ ] Automated compliance reporting

## License

Proprietary - PreciAgro Platform

