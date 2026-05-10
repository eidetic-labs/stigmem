"""Phase 4c coverage: OpenTelemetry tracing wrapper unit tests.

Covers ``stigmem_node.tracing``.  The OTel SDK is not installed in the
test image, so the disabled-path branches dominate; SDK-required branches
are skipped with an explicit reason.

The module owns two globals (``_OTEL_ENABLED`` / ``_tracer``).  The
``_reset_tracing_globals`` autouse fixture restores them between tests so
no test can leak enabled-state into a sibling.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

import stigmem_node.tracing as tracing_mod

# ---------------------------------------------------------------------------
# Global-state guard: every test in this file gets a fresh disabled tracer.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_tracing_globals() -> Generator[None, None, None]:
    saved_enabled = tracing_mod._OTEL_ENABLED
    saved_tracer = tracing_mod._tracer
    tracing_mod._OTEL_ENABLED = False
    tracing_mod._tracer = None
    try:
        yield
    finally:
        tracing_mod._OTEL_ENABLED = saved_enabled
        tracing_mod._tracer = saved_tracer


# ---------------------------------------------------------------------------
# is_enabled
# ---------------------------------------------------------------------------


def test_is_enabled_returns_false_when_not_initialised() -> None:
    assert tracing_mod.is_enabled() is False


# ---------------------------------------------------------------------------
# _NoopSpan — every method is a no-op (just must not raise).
# ---------------------------------------------------------------------------


def test_noop_span_set_attribute_is_silent() -> None:
    span = tracing_mod._NoopSpan()
    span.set_attribute("foo", "bar")  # must not raise


def test_noop_span_record_exception_is_silent() -> None:
    span = tracing_mod._NoopSpan()
    span.record_exception(ValueError("ignored"))
    span.record_exception(RuntimeError("also ignored"), escaped=True)


def test_noop_span_set_status_is_silent() -> None:
    span = tracing_mod._NoopSpan()
    span.set_status("ok")
    span.set_status("error", "with description")


def test_noop_span_add_event_is_silent() -> None:
    span = tracing_mod._NoopSpan()
    span.add_event("event-name")
    span.add_event("event-with-attrs", attributes={"key": "val"})


# ---------------------------------------------------------------------------
# start_span — disabled path
# ---------------------------------------------------------------------------


def test_start_span_yields_noop_when_disabled() -> None:
    with tracing_mod.start_span("test.span") as span:
        assert isinstance(span, tracing_mod._NoopSpan)
        # Exercise the full noop API inside the span context.
        span.set_attribute("k", "v")
        span.add_event("x")


def test_start_span_with_initial_attributes_disabled_path() -> None:
    """initial_attributes are only applied on the enabled path; on the
    disabled path the call must still succeed without setting anything."""
    with tracing_mod.start_span("test.span", tenant="alpha", count=3) as span:
        assert isinstance(span, tracing_mod._NoopSpan)


def test_start_span_disabled_does_not_swallow_exceptions() -> None:
    with pytest.raises(ValueError, match="boom"), tracing_mod.start_span("test.span"):
        raise ValueError("boom")


# ---------------------------------------------------------------------------
# start_span — enabled path (uses a fake tracer; no real OTel needed).
# ---------------------------------------------------------------------------


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.recorded_exceptions: list[BaseException] = []
        self.status: tuple[Any, str | None] | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def record_exception(self, exc: BaseException, *, escaped: bool = False) -> None:
        self.recorded_exceptions.append(exc)

    def set_status(self, status: Any, description: str | None = None) -> None:
        self.status = (status, description)


class _FakeTracer:
    def __init__(self) -> None:
        self.last_span = _FakeSpan()

    def start_as_current_span(self, name: str) -> Any:
        outer = self

        from collections.abc import Iterator
        from contextlib import contextmanager

        @contextmanager
        def _cm() -> Iterator[_FakeSpan]:
            yield outer.last_span

        return _cm()


def test_start_span_enabled_sets_initial_attributes() -> None:
    tracer = _FakeTracer()
    tracing_mod._OTEL_ENABLED = True
    tracing_mod._tracer = tracer

    with tracing_mod.start_span("op", tenant="beta", count=7) as span:
        assert span is tracer.last_span
        assert span.attributes == {"tenant": "beta", "count": 7}


def test_start_span_enabled_reraises_exception() -> None:
    """On exception inside the span, the wrapper must re-raise after the
    best-effort record/status block (which is itself wrapped in try/except
    so a missing ``opentelemetry.trace.StatusCode`` cannot mask the
    original exception)."""
    tracer = _FakeTracer()
    tracing_mod._OTEL_ENABLED = True
    tracing_mod._tracer = tracer

    with pytest.raises(ValueError, match="explode"), tracing_mod.start_span("op"):
        raise ValueError("explode")


def test_start_span_enabled_records_exception_when_otel_trace_present() -> None:
    """When ``opentelemetry.trace`` is importable, the wrapper records the
    exception and sets an error status before re-raising.  Skipped when
    the SDK is not installed (record_exception is never called because
    the StatusCode import inside the try-block fails first)."""
    pytest.importorskip("opentelemetry.trace", reason="opentelemetry not installed")
    tracer = _FakeTracer()
    tracing_mod._OTEL_ENABLED = True
    tracing_mod._tracer = tracer

    with pytest.raises(ValueError, match="explode"), tracing_mod.start_span("op"):
        raise ValueError("explode")

    assert any(
        isinstance(e, ValueError) for e in tracer.last_span.recorded_exceptions
    )
    assert tracer.last_span.status is not None


# ---------------------------------------------------------------------------
# init_tracing — SDK absent path
# ---------------------------------------------------------------------------


def test_init_tracing_warns_and_returns_when_sdk_absent(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When _OTEL_SDK_AVAILABLE is False, init_tracing must log a warning
    and leave _OTEL_ENABLED False."""
    monkeypatch.setattr(tracing_mod, "_OTEL_SDK_AVAILABLE", False)
    with caplog.at_level("WARNING", logger="stigmem"):
        tracing_mod.init_tracing("svc.test", "http://collector.example/")
    assert tracing_mod._OTEL_ENABLED is False
    assert tracing_mod._tracer is None
    assert any(
        "opentelemetry-sdk is not installed" in rec.getMessage() for rec in caplog.records
    )


# ---------------------------------------------------------------------------
# init_tracing — SDK-present path (skipped when SDK is absent in this env).
# ---------------------------------------------------------------------------


def test_init_tracing_with_sdk_sets_enabled_flag() -> None:
    """When the OTel SDK is available, init_tracing should set _OTEL_ENABLED.

    The OTLP exporters are optional; the function tolerates their absence
    by simply not adding a span processor.  This test only asserts the
    enabled flag and a non-None tracer."""
    pytest.importorskip("opentelemetry.sdk.trace", reason="opentelemetry-sdk not installed")
    tracing_mod.init_tracing("svc.test", "")
    assert tracing_mod._OTEL_ENABLED is True
    assert tracing_mod._tracer is not None


def test_init_tracing_with_sdk_and_http_endpoint() -> None:
    """init_tracing with a non-empty endpoint exercises the OTLP-HTTP exporter
    branch (and falls back to gRPC if HTTP is missing)."""
    pytest.importorskip("opentelemetry.sdk.trace", reason="opentelemetry-sdk not installed")
    tracing_mod.init_tracing("svc.test", "http://collector.example/")
    assert tracing_mod._OTEL_ENABLED is True
    assert tracing_mod._tracer is not None


def test_init_tracing_real_span_records_exception() -> None:
    """With the real OTel SDK loaded, the exception path inside start_span
    successfully imports StatusCode, calls record_exception, and sets the
    error status before re-raising."""
    pytest.importorskip("opentelemetry.sdk.trace", reason="opentelemetry-sdk not installed")
    tracing_mod.init_tracing("svc.test", "")

    with pytest.raises(RuntimeError, match="kaboom"), tracing_mod.start_span("op", attr="value"):
        raise RuntimeError("kaboom")
