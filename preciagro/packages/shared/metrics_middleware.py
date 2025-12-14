"""FastAPI middleware for automatic metrics collection."""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import record_http_request

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically collect HTTP metrics."""
    
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        # Record start time
        start_time = time.time()
        
        # Get endpoint (simplified path without query params)
        endpoint = request.url.path
        method = request.method
        
        # Process request
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            # Record error
            logger.error(f"Request failed: {e}")
            status = 500
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            record_http_request(
                service=self.service_name,
                endpoint=endpoint,
                method=method,
                status=status,
                duration=duration
            )
        
        return response


def add_metrics_middleware(app, service_name: str) -> None:
    """Add metrics middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service for metric labels
    
    Example:
        from fastapi import FastAPI
        from preciagro.packages.shared.metrics_middleware import add_metrics_middleware
        
        app = FastAPI()
        add_metrics_middleware(app, "my-service")
    """
    app.add_middleware(MetricsMiddleware, service_name=service_name)
    logger.info(f"Metrics middleware added for service: {service_name}")
