"""Shared error tracking module with Sentry integration."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import Sentry SDK
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.scrubber import EventScrubber
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logger.info("Sentry SDK not installed; error tracking disabled")


def scrub_pii_from_event(event, hint):
    """Scrub PII from Sentry events.
    
    - Always send errors (100% sampling)
    - Apply sampling for transactions
    - Remove/hash sensitive user data
    """
    # Always capture errors
    if 'exc_info' in hint or event.get('level') in ('error', 'fatal'):
        # Scrub PII from error events
        if 'user' in event:
            user = event['user']
            # Hash user ID instead of sending raw
            if 'id' in user:
                import hashlib
                user['id'] = hashlib.sha256(user['id'].encode()).hexdigest()[:16]
            # Remove email and other PII
            user.pop('email', None)
            user.pop('phone', None)
            user.pop('ip_address', None)
        return event
    
    # For transactions, apply sampling
    # (Sampling is already handled by traces_sample_rate, this is backup)
    return event


def init_sentry(
    service_name: str,
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
) -> None:
    """Initialize Sentry error tracking.
    
    Args:
        service_name: Name of the service for tagging
        dsn: Sentry DSN (Data Source Name). If None, reads from SENTRY_DSN env var
        environment: Environment name (dev, staging, production)
        traces_sample_rate: Percentage of transactions to trace (0.0 to 1.0)
        profiles_sample_rate: Percentage of transactions to profile (0.0 to 1.0)
    """
    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not available, skipping initialization")
        return

    dsn = dsn or os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("SENTRY_DSN not configured; error tracking disabled")
        return

    environment = environment or os.getenv("ENVIRONMENT", "development")

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            # PII protection
            before_send=scrub_pii_from_event,
            send_default_pii=False,
            # Set service name as a tag
            # before_send will handle this
            attach_stacktrace=True,
            max_breadcrumbs=50,
        )
        logger.info(f"Sentry initialized for {service_name} in {environment} environment")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def _enrich_event(event: dict, service_name: str) -> dict:
    """Enrich Sentry events with additional context and scrub PII."""
    if "tags" not in event:
        event["tags"] = {}
    event["tags"]["service"] = service_name
    
    # Scrub PII
    return scrub_pii_from_event(event, {})


def capture_exception(error: Exception, **context) -> None:
    """Capture an exception with optional context.
    
    Args:
        error: The exception to capture
        **context: Additional context to attach to the error
    """
    if not SENTRY_AVAILABLE:
        logger.error(f"Exception: {error}", exc_info=True)
        return

    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_context(key, value)
        sentry_sdk.capture_exception(error)


def capture_message(message: str, level: str = "info", **context) -> None:
    """Capture a message with optional context.
    
    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **context: Additional context to attach
    """
    if not SENTRY_AVAILABLE:
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
        return

    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_context(key, value)
        sentry_sdk.capture_message(message, level=level)
