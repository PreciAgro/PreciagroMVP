# Security Hardening Guide

## Overview

This guide covers the security features implemented in PreciagroMVP and how to use them.

## Features

### 1. Rate Limiting 🛡️

Distributed rate limiting using Redis with per-IP, per-user, and per-API-key tracking.

#### Usage

```python
from slowapi import Limiter
from preciagro.packages.shared.rate_limiting import create_limiter, add_rate_limiting

# Initialize rate limiter
limiter = create_limiter(
    redis_url="redis://localhost:6379/0",
    default_limits=["100/minute", "1000/hour"]
)

# Add to FastAPI app
add_rate_limiting(app, limiter)

# Apply to specific endpoints
@app.get("/api/endpoint")
@limiter.limit("10/minute")  # Override default
async def my_endpoint():
    return {"status": "ok"}
```

#### Configuration

```env
REDIS_URL=redis://localhost:6379/0
```

---

### 2. CORS Configuration 🌐

Environment-based CORS policies with secure defaults.

#### Usage

```python
from fastapi.middleware.cors import CORSMiddleware  
from preciagro.packages.shared.cors_config import get_cors_config

# Get environment-specific CORS config
cors_config = get_cors_config(environment="production")

# Add to FastAPI app
app.add_middleware(CORSMiddleware, **cors_config)
```

#### Configuration

```env
# Comma-separated list of allowed origins
CORS_ORIGINS=https://app.preciagro.com,https://www.preciagro.com

# OR use environment-based defaults
ENVIRONMENT=production  # production|staging|development
```

**Defaults by Environment:**
- **Production**: Only specific domains (never `*`)
- **Staging**: Staging domain + localhost
- **Development**: Localhost ports

---

### 3. Input Validation ✅

Request size limits and content-type validation.

#### Usage

```python
from preciagro.packages.shared.validation import (
    add_request_size_limit,
    validate_content_type,
    PaginationParams
)

# Add request size limit middleware
add_request_size_limit(app, max_size=10*1024*1024)  # 10MB

# Add content-type validation middleware
app.middleware("http")(validate_content_type)

# Use pagination model
@app.get("/items")
async def get_items(pagination: PaginationParams):
    return {"page": pagination.page, "size": pagination.page_size}
```

#### Configuration

```env
MAX_REQUEST_SIZE_BYTES=10485760  # 10MB
```

---

### 4. HTTPS/TLS 🔒

SSL/TLS encryption for secure communication.

#### Generate Development Certificates

```bash
python scripts/generate_ssl_cert.py
```

This creates:
- `certs/cert.pem` - SSL certificate
- `certs/key.pem` - Private key

#### Enable HTTPS

```env
ENABLE_HTTPS=true
SSL_CERT_FILE=certs/cert.pem
SSL_KEY_FILE=certs/key.pem
```

#### Run with HTTPS

```bash
uvicorn app:app --ssl-keyfile=certs/key.pem --ssl-certfile=certs/cert.pem
```

**⚠️ WARNING**: Self-signed certificates are for DEVELOPMENT ONLY. Use proper certificates in production (Let's Encrypt, etc.).

---

## Security Best Practices

### 1. Environment Variables

Never commit secrets to git:
- Use `.env` files (gitignored)
- Use environment-specific configs
- Rotate API keys regularly

### 2. Rate Limiting

Apply appropriate limits:
- **Public endpoints**: 10-60/minute
- **Authenticated endpoints**: 100-300/minute
- **Admin endpoints**: Strict limits

### 3. CORS

- **Never** use `["*"]` in production
- Specify exact domains
- Enable credentials only when needed

### 4. Input Validation

- Always validate user input
- Use Pydantic models
- Implement request size limits
- Validate content-types

### 5. HTTPS

- Always use HTTPS in production
- Use HTTP Strict Transport Security (HSTS)
- Keep certificates up to date

---

## Dependency Security

### Check for Vulnerabilities

```bash
# Install security tools
pip install pip-audit safety

# Run security audit
pip-audit

# Alternative
safety check
```

### Update Dependencies

```bash
# Update specific package
pip install --upgrade package-name

# Update all (carefully!)
pip list --outdated
```

---

## Quick Reference

| Feature | File | Purpose |
|---------|------|---------|
| Rate Limiting | `shared/rate_limiting.py` | Distributed rate limits |
| CORS Config | `shared/cors_config.py` | Environment-based CORS |
| Validation | `shared/validation.py` | Input validation helpers |
| SSL Certs | `scripts/generate_ssl_cert.py` | Generate dev certificates |

---

## Troubleshooting

### Rate Limiting Not Working
- Check Redis connection
- Verify `REDIS_URL` environment variable
- Check logs for rate limit errors

### CORS Errors
- Verify `CORS_ORIGINS` includes the requesting origin
- Check browser console for exact error
- Ensure protocol matches (https vs http)

### HTTPS Certificate Errors
- Regenerate certificates
- Check file paths in environment variables
- Browser may show warnings for self-signed certs (expected in dev)

---

For more information, see the implementation plan and walkthrough artifacts.
