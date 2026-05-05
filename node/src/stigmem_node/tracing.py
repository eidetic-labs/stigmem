"""OpenTelemetry tracing setup — spec §23 (Phase 13).

Activated when ``opentelemetry-sdk`` is installed and
``STIGMEM_OTEL_ENABLED=true``.  All calls are no-ops when the SDK is absent
or the feature is disabled, so the node runs without the dependency.

Usage from routes::

    from .tracing import start_span

    with start_span("stigmem.assert_fact") as span:
        span.set_attribute("stigmem.tenant", tenant_id)
        # ... do work ...
"""

from __future__ import annotations

import contextlib
import time
from typing import Any, Generator

_OTEL_ENABLED = False
_tracer: Any = None


try:
    from opentelemetry import trace as _otel_trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    _OTEL_SDK_AVAILABLE = True
except ImportError:
    _OTEL_SDK_AVAILABLE = False


def init_tracing(service_name: str, otlp_endpoint: str) -> None:
    """Initialize the OTel SDK.  Called once at app startup when otel_enabled=True."""
    global _OTEL_ENABLED, _tracer
    if not _OTEL_SDK_AVAILABLE:
        import logging
        logging.getLogger("stigmem").warning(
            "STIGMEM_OTEL_ENABLED=true but opentelemetry-sdk is not installed; "
            "install stigmem-node[observability] to enable tracing."
        )
        return

    from opentelemetry import trace as _otel_trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        _exporter_added = False
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
            _exporter_added = True
        except ImportError:
            pass

        if not _exporter_added:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-not-found]
                    OTLPSpanExporter as GrpcOTLPSpanExporter,
                )
                grpc_exporter = GrpcOTLPSpanExporter(endpoint=otlp_endpoint)
                provider.add_span_processor(BatchSpanProcessor(grpc_exporter))
            except ImportError:
                pass  # neither OTLP exporter installed; traces collected locally only

    _otel_trace.set_tracer_provider(provider)
    _tracer = _otel_trace.get_tracer("stigmem.node", schema_url="https://opentelemetry.io/schemas/1.21.0")
    _OTEL_ENABLED = True


class _NoopSpan:
    """Minimal no-op span used when OTel is disabled."""
    def set_attribute(self, key: str, value: Any) -> None:  # noqa: ARG002
        pass

    def record_exception(self, exc: BaseException, *, escaped: bool = False) -> None:  # noqa: ARG002
        pass

    def set_status(self, status: Any, description: str | None = None) -> None:  # noqa: ARG002
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:  # noqa: ARG002
        pass


@contextlib.contextmanager
def start_span(name: str, **initial_attributes: Any) -> Generator[_NoopSpan | Any, None, None]:
    """Start a span as a context manager.

    Yields a live OTel ``Span`` (when enabled) or a no-op ``_NoopSpan``
    (when disabled).  Always safe to call; never blocks.
    """
    if not _OTEL_ENABLED or _tracer is None:
        yield _NoopSpan()
        return

    with _tracer.start_as_current_span(name) as span:
        for key, value in initial_attributes.items():
            span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            try:
                from opentelemetry.trace import StatusCode
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
            except Exception:  # noqa: BLE001  # nosec B110
                pass
            raise


def is_enabled() -> bool:
    return _OTEL_ENABLED
