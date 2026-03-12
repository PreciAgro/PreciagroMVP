# Security & Access Engine - Architecture Document

## Overview

The Security & Access Engine is the **foundational security layer** for PreciAgro. It implements a zero-trust architecture with comprehensive identity, authentication, authorization, encryption, and audit capabilities.

## Design Principles

1. **Zero Trust** - Every request is authenticated and authorized
2. **Least Privilege** - Actors only get minimum required permissions
3. **Defense in Depth** - Multiple layers of security controls
4. **Audit Everything** - Immutable logs for all security events
5. **Encryption Everywhere** - Data at rest and in transit
6. **Short-Lived Credentials** - Access tokens expire in 15 minutes
7. **Explicit Denial** - Default deny, explicit allow

## Architecture Layers

### 1. Identity Layer

**Actor-Based Model**
- **Human**: Farmers, agronomists, admins, support staff
- **Device**: Mobile apps, edge nodes, drones
- **Service**: Engine-to-engine communication
- **External**: Partner APIs, third-party integrations

**Trust Levels**
- `unverified` - New actors, limited access
- `verified` - Email/phone verified
- `trusted` - Established actors with history
- `high_trust` - Admin/system actors

### 2. Authentication Layer

**Methods Supported**
- Password-based (Argon2id/bcrypt)
- OTP (SMS/Email)
- Multi-Factor Authentication (TOTP)
- Device certificates (future)
- mTLS for service-to-service (future)

**Token Lifecycle**
- Access tokens: 15 minutes
- Refresh tokens: 7 days with rotation
- Service tokens: Configurable
- Device tokens: Per-device

### 3. Authorization Layer

**RBAC (Role-Based Access Control)**
- Roles: farmer, agronomist, admin, support
- Permissions: resource:action pairs
- Role-permission assignments
- Actor-role assignments with expiry

**ABAC (Attribute-Based Access Control)**
- Subject attributes: role, region, trust_level, crop_type
- Resource attributes: type, owner, region
- Environment attributes: time, online/offline, confidence
- Policy evaluation with priority

**Policy Example**
```json
{
  "subject": {
    "role": "farmer",
    "region": "EU"
  },
  "resource": {
    "type": "farm"
  },
  "action": "read",
  "conditions": {
    "region": {"$in": ["EU", "PL"]},
    "trust_level": {"$gte": "verified"}
  },
  "effect": "allow"
}
```

### 4. Encryption Layer

**Envelope Encryption**
- Master key (from KMS or env)
- Data encryption keys (DEKs) per domain
- Automatic key rotation (90 days)
- Key versioning

**Algorithms**
- Data at rest: AES-256-GCM
- Data in transit: TLS 1.3
- Key encryption: AES-GCM with master key

**Key Management**
- Local (dev) or KMS (production)
- Key rotation without downtime
- Key metadata tracking

### 5. Audit Layer

**Immutable Logs**
- Append-only audit table
- Tamper-evident hashing
- Time-ordered events
- Structured JSON metadata

**Event Types**
- Authentication events
- Authorization decisions
- Data access/modify/delete
- AI recommendations
- Admin actions
- Offline syncs
- Key rotations

### 6. AI Safety Layer

**Prompt Validation**
- Injection pattern detection
- Length limits
- Sanitization

**Output Gating**
- Confidence thresholds
- Unsafe content detection
- Policy-based filtering

## Data Flow

### Authentication Flow

```
1. User submits credentials
   ↓
2. Identity Service validates actor
   ↓
3. Password Service verifies password
   ↓
4. MFA check (if enabled)
   ↓
5. Token Service generates tokens
   ↓
6. Audit Service logs event
   ↓
7. Return tokens to client
```

### Authorization Flow

```
1. Request with token
   ↓
2. Token Service verifies token
   ↓
3. Authorization Service checks RBAC
   ↓
4. Authorization Service checks ABAC
   ↓
5. Audit Service logs decision
   ↓
6. Allow or deny request
```

### Encryption Flow

```
1. Request to encrypt data
   ↓
2. Encryption Service gets/creates DEK
   ↓
3. Encrypt data with DEK
   ↓
4. Return encrypted data + key reference
   ↓
5. Store encrypted data with key reference
```

## Database Schema

### Core Tables

- `security_actors` - Actor identities
- `security_roles` - RBAC roles
- `security_permissions` - Permissions
- `security_role_permissions` - Role-permission mapping
- `security_actor_roles` - Actor-role assignments
- `security_tokens` - Token storage
- `security_mfa_devices` - MFA devices
- `security_encryption_keys` - Key management
- `security_audit_logs` - Audit trail
- `security_abac_policies` - ABAC policies

### Relationships

```
Actor ──┬──> ActorRole ──> Role ──> RolePermission ──> Permission
        │
        ├──> Token
        │
        ├──> MFADevice
        │
        └──> AuditLog
```

## Security Considerations

### Threat Model

**Assumed Threats**
- Account compromise
- Device theft
- API probing
- Insider abuse
- Offline data tampering

**Mitigations**
- Short-lived tokens
- Token rotation
- MFA enforcement
- Audit logging
- Encryption at rest
- Rate limiting
- Trust degradation

### Key Security Features

1. **Token Security**
   - Short expiration (15 min)
   - Refresh rotation
   - Revocation support
   - JTI tracking

2. **Password Security**
   - Argon2id hashing
   - Salted
   - Memory-hard
   - Rehash on upgrade

3. **Encryption Security**
   - Envelope encryption
   - Key rotation
   - No key exposure
   - KMS integration ready

4. **Audit Security**
   - Immutable logs
   - Tamper-evident hashing
   - Append-only
   - Retention policies

## Scalability

### Horizontal Scaling
- Stateless services
- Database-backed
- Redis for rate limiting
- Shared database

### Performance Optimizations
- Database indexes
- Connection pooling
- Token caching (future)
- Policy caching (future)

## Compliance

### GDPR Ready
- Consent tracking hooks
- Data deletion support
- Data export support
- Right to be forgotten

### Regional Compliance
- Data residency policies
- Region-based access control
- Audit requirements

## Future Enhancements

1. **Device Certificates**
   - X.509 certificate management
   - Certificate revocation lists
   - Device attestation

2. **mTLS**
   - Service-to-service TLS
   - Certificate-based auth
   - Mutual authentication

3. **OAuth2/OIDC**
   - Standard protocol support
   - Third-party integrations
   - SSO support

4. **Advanced Features**
   - Biometric authentication
   - Hardware security modules
   - Threat detection
   - Automated compliance reporting

## Deployment

### Production Checklist

- [ ] Generate RSA keys for JWT
- [ ] Set strong master key (32 bytes)
- [ ] Configure KMS (AWS/Azure/GCP)
- [ ] Enable audit logging
- [ ] Set up monitoring
- [ ] Configure rate limiting
- [ ] Enable MFA for admins
- [ ] Set up key rotation schedule
- [ ] Configure backup/restore
- [ ] Set retention policies
- [ ] Enable compliance features

## Monitoring

### Key Metrics

- Authentication success/failure rates
- Token issuance/revocation rates
- Permission check latency
- Encryption/decryption operations
- Audit log volume
- Failed authorization attempts

### Alerts

- High authentication failure rate
- Unusual permission denials
- Token abuse patterns
- Encryption key expiration warnings
- Audit log storage issues

## References

- [README.md](./README.md) - User guide
- [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - Integration examples
- API Documentation - FastAPI auto-generated docs at `/docs`

