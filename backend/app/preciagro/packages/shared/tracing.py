"""Shared distributed tracing module with OpenTelemetry."""

from __future__ import annotations

import contextlib
import logging
import os
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    logger.info("OpenTelemetry not installed; tracing disabled")


def get_trace_sample_rate(environment: str = None) -> float:
    """Get trace sample rate based on environment.
    
    Args:
        environment: Environment name (development, staging, production)
    
    Returns:
        Sample rate (0.0 to 1.0)
    """
    environment = environment or os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        return 0.05  # 5% sampling in production
    elif environment == "staging":
        return 1.0   # 100% sampling in staging
    else:
        return 1.0   # 100% sampling in development


def init_tracing(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    environment: Optional[str] = None,
) -> None:
    """Initialize OpenTelemetry tracing with OTLP exporter.
    
    Args:
        service_name: Name of the service for identification
        otlp_endpoint: OTLP collector endpoint. If None, reads from OTEL_EXPORTER_OTLP_ENDPOINT
        environment: Environment name (dev, staging, production)
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping tracing initialization")
        return

    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not configured; tracing disabled")
        return

    environment = environment or os.getenv("ENVIRONMENT", "development")

    try:
        # Get sample rate for environment
        sample_rate = get_trace_sample_rate(environment)
        
        # Create resource with service information
        resource = Resource(attributes={
            SERVICE_NAME: service_name,
            "environment": environment,
        })

        # Create tracer provider with sampling
        from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
        sampler = ParentBasedTraceIdRatio(sample_rate)
        provider = TracerProvider(resource=resource, sampler=sampler)

        # Add OTLP span processor
        otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        logger.info(f"OpenTelemetry tracing initialized for {service_name}")
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")


def instrument_fastapi(app) -> None:
    """Instrument FastAPI application for automatic tracing.
    
    Args:
        app: FastAPI application instance
    """
    if not OTEL_AVAILABLE:
        return

    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")


def instrument_sqlalchemy(engine) -> None:
    """Instrument SQLAlchemy engine for database query tracing.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    if not OTEL_AVAILABLE:
        return

    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument SQLAlchemy: {e}")


def instrument_redis() -> None:
    """Instrument Redis for cache operation tracing."""
    if not OTEL_AVAILABLE:
        return

    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument Redis: {e}")


@contextlib.contextmanager
def start_span(name: str, attributes: Optional[dict] = None) -> Iterator[None]:
    """Start a custom span for tracing.
    
    Args:
        name: Name of the span
        attributes: Optional attributes to attach to the span
    
    Example:
        with start_span("process_image", {"image_id": image_id}):
            # Your code here
            pass
    """
    if not OTEL_AVAILABLE or trace is None:
        yield
        return

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        yield
