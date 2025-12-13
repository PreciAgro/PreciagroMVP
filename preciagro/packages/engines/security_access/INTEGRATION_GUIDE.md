# Security & Access Engine - Integration Guide

This guide explains how to integrate the Security & Access Engine with other PreciAgro engines and the API Gateway.

## API Gateway Integration

### 1. Add Security Middleware

In your API Gateway (`preciagro/apps/api_gateway/main.py`):

```python
from preciagro.packages.engines.security_access.app.middleware.gateway_integration import SecurityGatewayMiddleware

app.add_middleware(SecurityGatewayMiddleware)
```

### 2. Protect Routes

Use FastAPI dependencies to require authentication:

```python
from fastapi import Depends
from preciagro.packages.engines.security_access.app.services.token_service import TokenService
from preciagro.packages.engines.security_access.app.db.base import get_db

async def require_auth(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Dependency to require authentication."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = authorization.split(" ", 1)[1]
    token_service = TokenService(db)
    payload = await token_service.verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload

# Use in routes
@router.get("/protected")
async def protected_route(auth: dict = Depends(require_auth)):
    actor_id = auth.get("sub")
    # ... your logic
```

### 3. Check Permissions

```python
from preciagro.packages.engines.security_access.app.services.authorization_service import AuthorizationService

async def require_permission(
    resource: str,
    action: str,
    auth: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Dependency to require specific permission."""
    actor_id = auth.get("sub")
    authz_service = AuthorizationService(db)
    
    allowed = await authz_service.check_permission(
        actor_id,
        resource,
        action,
    )
    
    if not allowed:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return auth

# Use in routes
@router.get("/farms/{farm_id}")
async def get_farm(
    farm_id: str,
    auth: dict = Depends(lambda: require_permission("farm", "read")),
):
    # ... your logic
```

## Engine-to-Engine Integration

### Service-to-Service Authentication

For service-to-service communication, use service tokens:

```python
from preciagro.packages.engines.security_access.app.services.token_service import TokenService
from preciagro.packages.engines.security_access.app.db.models import ActorType, TokenType

# Create service actor
identity_service = IdentityService(db)
service_actor = await identity_service.create_actor(
    actor_type=ActorType.SERVICE,
    service_name="crop_intelligence",
    service_endpoint="http://localhost:8104",
)

# Generate service token
token_service = TokenService(db)
service_token, _ = await token_service.create_access_token(
    service_actor.actor_id,
    scopes=["crop_intelligence:read", "crop_intelligence:write"],
)
```

### Calling Other Engines with Auth

```python
import httpx

async def call_geo_context(location: dict, service_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8102/v1/context",
            json=location,
            headers={"Authorization": f"Bearer {service_token}"},
        )
        return response.json()
```

## AI Safety Integration

### In AgroLLM Engine

```python
from preciagro.packages.engines.security_access.app.services.ai_safety_service import AISafetyService

async def generate_recommendation(
    actor_id: str,
    prompt: str,
    db: AsyncSession,
):
    ai_safety = AISafetyService(db)
    
    # Validate prompt
    is_safe, sanitized_prompt, _ = await ai_safety.validate_prompt(
        actor_id,
        prompt,
    )
    
    if not is_safe:
        raise ValueError("Unsafe prompt detected")
    
    # Generate recommendation (your LLM call)
    recommendation = await your_llm.generate(sanitized_prompt)
    confidence = recommendation.get("confidence", 0.0)
    
    # Gate output
    allowed, filtered_rec = await ai_safety.gate_recommendation(
        actor_id,
        recommendation,
        confidence,
    )
    
    if not allowed:
        raise ValueError("Recommendation blocked by safety gate")
    
    return filtered_rec
```

## Offline/Edge Integration

### Device Registration

```python
from preciagro.packages.engines.security_access.app.services.identity_service import IdentityService

# Register device
identity_service = IdentityService(db)
device_actor = await identity_service.create_actor(
    actor_type=ActorType.DEVICE,
    device_name="Farmer Mobile App",
    device_fingerprint="device_unique_id_hash",
    region="EU",
)
```

### Offline Action Signing

```python
import hashlib
import hmac

def sign_offline_action(action: dict, device_secret: str) -> str:
    """Sign an offline action."""
    action_str = json.dumps(action, sort_keys=True)
    signature = hmac.new(
        device_secret.encode(),
        action_str.encode(),
        hashlib.sha256,
    ).hexdigest()
    return signature

# On sync, verify signature
def verify_offline_action(action: dict, signature: str, device_secret: str) -> bool:
    expected = sign_offline_action(action, device_secret)
    return hmac.compare_digest(expected, signature)
```

## Encryption Integration

### Encrypting Sensitive Data

```python
from preciagro.packages.engines.security_access.app.services.encryption_service import EncryptionService
import base64

encryption_service = EncryptionService(db)

# Encrypt
sensitive_data = b"farmer personal information"
encrypted, key_ref = await encryption_service.encrypt_data(sensitive_data)

# Store encrypted data and key reference
# In your database:
# encrypted_field = base64.b64encode(encrypted).decode()
# key_reference = key_ref

# Decrypt
encrypted_bytes = base64.b64decode(encrypted_field)
decrypted = await encryption_service.decrypt_data(encrypted_bytes, key_reference)
```

## Audit Logging Integration

### Logging Custom Events

```python
from preciagro.packages.engines.security_access.app.services.audit_service import AuditService
from preciagro.packages.engines.security_access.app.db.models import AuditEventType

audit_service = AuditService(db)

# Log custom event
await audit_service.log_event(
    event_type=AuditEventType.DATA_ACCESS,
    actor_id=actor_id,
    resource_type="farm",
    resource_id=farm_id,
    action="read",
    success=True,
    ip_address=request.client.host,
    metadata={"additional": "context"},
)
```

## Example: Complete Protected Endpoint

```python
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from preciagro.packages.engines.security_access.app.services.token_service import TokenService
from preciagro.packages.engines.security_access.app.services.authorization_service import AuthorizationService
from preciagro.packages.engines.security_access.app.services.audit_service import AuditService
from preciagro.packages.engines.security_access.app.db.base import get_db
from preciagro.packages.engines.security_access.app.db.models import AuditEventType

router = APIRouter()

async def get_authenticated_actor(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get authenticated actor from token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = authorization.split(" ", 1)[1]
    token_service = TokenService(db)
    payload = await token_service.verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload

@router.get("/farms/{farm_id}")
async def get_farm(
    farm_id: str,
    auth: dict = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
):
    """Get farm with authorization check."""
    actor_id = auth.get("sub")
    
    # Check permission
    authz_service = AuthorizationService(db)
    allowed = await authz_service.check_permission(
        actor_id,
        "farm",
        "read",
        context={"farm_id": farm_id},
    )
    
    if not allowed:
        audit_service = AuditService(db)
        await audit_service.log_permission_event(
            actor_id,
            "farm",
            farm_id,
            "read",
            False,
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Log access
    audit_service = AuditService(db)
    await audit_service.log_data_access(
        actor_id,
        "farm",
        farm_id,
        "read",
    )
    
    # Your business logic
    # farm = await get_farm_from_db(farm_id)
    # return farm
    
    return {"farm_id": farm_id, "status": "ok"}
```

## Testing with Security Engine

### Mock Authentication for Tests

```python
import pytest
from preciagro.packages.engines.security_access.app.services.token_service import TokenService
from preciagro.packages.engines.security_access.app.services.identity_service import IdentityService
from preciagro.packages.engines.security_access.app.db.models import ActorType, HumanRole

@pytest.fixture
async def test_actor(db):
    """Create test actor."""
    identity_service = IdentityService(db)
    actor = await identity_service.create_actor(
        actor_type=ActorType.HUMAN,
        email="test@example.com",
        role=HumanRole.FARMER,
    )
    return actor

@pytest.fixture
async def test_token(db, test_actor):
    """Create test token."""
    token_service = TokenService(db)
    token, _ = await token_service.create_access_token(test_actor.actor_id)
    return token

async def test_protected_endpoint(client, test_token):
    """Test protected endpoint."""
    response = await client.get(
        "/protected",
        headers={"Authorization": f"Bearer {test_token}"},
    )
    assert response.status_code == 200
```

## Configuration

### Environment Variables for Integration

```bash
# Security Engine URL
SECURITY_ACCESS_URL=http://localhost:8105

# Service-to-service token
SERVICE_AUTH_TOKEN=<service_token>

# Encryption master key (32 bytes)
ENCRYPTION_MASTER_KEY=<base64_encoded_key>

# JWT public key for verification
JWT_PUBLIC_KEY=<RSA_public_key>
```

## Best Practices

1. **Always validate tokens** before processing requests
2. **Check permissions** for all data access
3. **Log security events** for audit trail
4. **Encrypt sensitive data** at rest
5. **Use short-lived tokens** and rotate refresh tokens
6. **Implement rate limiting** to prevent abuse
7. **Validate AI outputs** before returning to users
8. **Sign offline actions** for sync validation

## Troubleshooting

### Token Verification Fails

- Check JWT algorithm matches (RS256 vs HS256)
- Verify public key is correct
- Check token expiration
- Ensure token is not revoked

### Permission Denied

- Check actor has required role
- Verify ABAC policies allow access
- Check context attributes match policy conditions
- Review audit logs for details

### Encryption Errors

- Verify master key is set correctly
- Check key reference format ("key_id:key_version")
- Ensure key is not expired or rotated
- Verify data encoding (base64)

## Support

For issues or questions, refer to the main README.md or contact the security team.

