"""Optional OpenTelemetry tracing helpers."""

from __future__ import annotations

import contextlib
import logging
from typing import Iterator

try:  # Lazy import to keep optional dependency
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
except Exception:  # noqa: BLE001
    trace = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def init_tracer(service_name: str) -> None:
    """Initialize an OTLP tracer if opentelemetry deps are available."""
    if trace is None:
        logger.info("OpenTelemetry not installed; tracing disabled")
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry tracer initialized for %s", service_name)


@contextlib.contextmanager
def start_span(name: str) -> Iterator[None]:
    """Start a span if tracing is available."""
    if trace is None:
        yield
        return
    tracer = trace.get_tracer("conversational-nlp")
    with tracer.start_as_current_span(name):
        yield
