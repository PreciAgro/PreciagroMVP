"""Configuration for the temporal logic engine."""

from typing import Optional

from pydantic import BaseSettings


class TemporalLogicConfig(BaseSettings):
    """Configuration for temporal logic engine."""

    # Database settings
    database_url: str = "postgresql://localhost:5432/preciagro"
    redis_url: str = "redis://localhost:6379/0"

    # ARQ settings
    arq_job_timeout: int = 300
    arq_max_jobs: int = 10
    arq_retry_jobs: bool = True
    arq_max_tries: int = 3

    # Rate limiting
    default_rate_limit: int = 100  # requests per hour
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    quiet_hours_timezone: str = "UTC"

    # Channel configurations
    whatsapp_access_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_webhook_verify_token: Optional[str] = None

    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None

    # Security
    # SECURITY: secret_key MUST be set via environment variable
    secret_key: str = ""  # Must be configured via environment
    access_token_expire_minutes: int = 30

    # Telemetry
    enable_metrics: bool = True
    metrics_port: int = 8001

    # Evaluation settings
    max_window_size: int = 86400  # 24 hours in seconds
    evaluation_interval: int = 60  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = TemporalLogicConfig()
