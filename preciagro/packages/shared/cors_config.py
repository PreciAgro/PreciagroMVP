"""Shared CORS configuration utilities."""

from __future__ import annotations

import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def get_cors_origins(environment: str = None) -> List[str]:
    """Get CORS allowed origins based on environment.
    
    Args:
        environment: Environment name (development, staging, production)
    
    Returns:
        List of allowed origins
    """
    environment = environment or os.getenv("ENVIRONMENT", "development")
    
    # Read from environment variable first
    cors_origins_env = os.getenv("CORS_ORIGINS")
    if cors_origins_env:
        origins = [origin.strip() for origin in cors_origins_env.split(",")]
        logger.info(f"Using CORS origins from environment: {origins}")
        return origins
    
    # Environment-specific defaults
    if environment == "production":
        # In production, never use wildcard
        origins = [
            "https://preciagro.com",
            "https://www.preciagro.com",
            "https://app.preciagro.com",
        ]
    elif environment == "staging":
        origins = [
            "https://staging.preciagro.com",
            "http://localhost:3000",
            "http://localhost:8080",
        ]
    else:  # development
        origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ]
    
    logger.info(f"Using default CORS origins for {environment}: {origins}")
    return origins


def get_cors_config(environment: str = None) -> dict:
    """Get complete CORS configuration.
    
    Args:
        environment: Environment name
    
    Returns:
        Dictionary with CORS configuration
    """
    environment = environment or os.getenv("ENVIRONMENT", "development")
    
    return {
        "allow_origins": get_cors_origins(environment),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-User-ID",
            "X-Request-ID",
        ],
        "expose_headers": [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 600,  # Cache preflight requests for 10 minutes
    }
