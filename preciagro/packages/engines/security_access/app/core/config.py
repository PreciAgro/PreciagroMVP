"""Configuration for Security & Access Engine."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings for Security & Access Engine."""
    
    ENV: str = "dev"
    ENGINE_NAME: str = "security_access"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    AUTO_CREATE_SCHEMA: bool = True
    
    # JWT Configuration
    JWT_SECRET_KEY: str = ""  # For HS256 (dev only)
    JWT_PRIVATE_KEY: str = ""  # RSA private key for RS256 (production)
    JWT_PUBLIC_KEY: str = ""  # RSA public key for RS256 (production)
    JWT_ALGORITHM: str = "RS256"  # RS256 for production, HS256 for dev
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access tokens
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Hashing
    PASSWORD_HASH_ALGORITHM: str = "argon2id"  # argon2id or bcrypt
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 65536  # 64 MB
    ARGON2_PARALLELISM: int = 4
    
    # Encryption & Key Management
    KMS_PROVIDER: str = "local"  # local, aws-kms, azure-keyvault, gcp-kms
    ENCRYPTION_KEY_ID: str = "default"  # Key ID for envelope encryption
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    KEY_ROTATION_INTERVAL_DAYS: int = 90
    
    # MFA Configuration
    MFA_ISSUER_NAME: str = "PreciAgro"
    TOTP_VALIDITY_WINDOW: int = 1  # Time steps to accept
    SMS_PROVIDER: str = "twilio"  # twilio, aws-sns, etc.
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # Device Certificate
    DEVICE_CERT_CA_PATH: Optional[str] = None
    DEVICE_CERT_VALIDITY_DAYS: int = 365
    
    # Service-to-Service Auth
    MTLS_ENABLED: bool = True
    MTLS_CA_CERT_PATH: Optional[str] = None
    MTLS_CLIENT_CERT_PATH: Optional[str] = None
    MTLS_CLIENT_KEY_PATH: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_LOG_ARCHIVE_ENABLED: bool = True
    
    # AI Safety Integration
    AI_SAFETY_ENABLED: bool = True
    AI_CONFIDENCE_THRESHOLD: float = 0.7
    AI_PROMPT_SANITIZATION_ENABLED: bool = True
    
    # Offline/Edge Security
    OFFLINE_TRUST_DEGRADATION_HOURS: int = 24
    OFFLINE_SYNC_REVALIDATION_ENABLED: bool = True
    
    # Compliance
    GDPR_ENABLED: bool = False  # Prepare for GDPR compliance
    DATA_RESIDENCY_ENFORCED: bool = False
    CONSENT_TRACKING_ENABLED: bool = False
    
    # External Service URLs
    API_GATEWAY_URL: str = "http://localhost:8000"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Feature Flags
    ENABLE_PROMETHEUS: bool = True
    DEBUG: bool = False
    DEV_MODE: bool = False  # Bypass some security checks in dev
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

