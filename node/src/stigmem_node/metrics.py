"""Prometheus metrics for the Stigmem reference node — spec §22.4, Phase 13.

If ``prometheus_client`` is installed, this module registers the full metric
set and exposes it via ``/metrics``.  If the package is absent, all operations
are no-ops so the node runs without the dependency.

Counters:
  stigmem_fact_write_total{principal, tenant}
  stigmem_fact_read_total{principal, tenant}
  stigmem_quota_breach_total{principal, tenant, dimension}
  stigmem_audit_event_total{event_type, tenant}
  stigmem_contradiction_total{tenant}
  stigmem_federation_ingress_total{peer_id, status}
  stigmem_federation_egress_total{peer_id, status}
  stigmem_subscription_event_total{delivery_type, status}
  stigmem_plugin_hook_fire_total{hook}
  stigmem_plugin_handler_invocation_total{hook, plugin}
  stigmem_plugin_handler_error_total{hook, plugin, error_type}
  stigmem_plugin_voting_decision_total{hook, decision}
  stigmem_plugin_registration_total{outcome, reason}

Histograms:
  stigmem_request_latency_seconds{route, method, status_code}
  stigmem_recall_ranker_duration_seconds{tenant}
  stigmem_capability_verify_duration_seconds{result}
  stigmem_plugin_hook_duration_seconds{hook}
  stigmem_plugin_handler_duration_seconds{hook, plugin}

Gauges:
  stigmem_subscription_connections_active{tenant}
  stigmem_replication_lag_seconds{peer_id}
  stigmem_plugin_registered_count
  stigmem_plugin_handlers_per_hook{hook}
"""

from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

logger = logging.getLogger("stigmem.metrics")

if TYPE_CHECKING:
    from starlette.responses import Response

try:
    import prometheus_client as _prom
    from prometheus_client import REGISTRY, Counter, Gauge, Histogram  # noqa: F401

    _ENABLED = True

    # ----- Counters -----
    FACT_WRITE = Counter(
        "stigmem_fact_write_total",
        "Total fact assertions",
        ["principal", "tenant"],
    )
    FACT_READ = Counter(
        "stigmem_fact_read_total",
        "Total fact read / recall queries",
        ["principal", "tenant"],
    )
    QUOTA_BREACH = Counter(
        "stigmem_quota_breach_total",
        "Total quota-exceeded (429) responses",
        ["principal", "tenant", "dimension"],
    )
    AUDIT_EVENT = Counter(
        "stigmem_audit_event_total",
        "Total audit events emitted (§22.3)",
        ["event_type", "tenant"],
    )
    CONTRADICTION = Counter(
        "stigmem_contradiction_total",
        "Total facts that triggered a contradiction on write",
        ["tenant"],
    )
    FEDERATION_INGRESS = Counter(
        "stigmem_federation_ingress_total",
        "Facts received via federation pull ingress",
        ["peer_id", "status"],
    )
    FEDERATION_EGRESS = Counter(
        "stigmem_federation_egress_total",
        "Facts served via federation pull egress",
        ["peer_id", "status"],
    )
    SUBSCRIPTION_EVENT = Counter(
        "stigmem_subscription_event_total",
        "Subscription delivery events",
        ["delivery_type", "status"],
    )
    PLUGIN_HOOK_FIRE = Counter(
        "stigmem_plugin_hook_fire_total",
        "Plugin hook dispatches",
        ["hook"],
    )
    PLUGIN_HANDLER_INVOCATION = Counter(
        "stigmem_plugin_handler_invocation_total",
        "Plugin handler invocations",
        ["hook", "plugin"],
    )
    PLUGIN_HANDLER_ERROR = Counter(
        "stigmem_plugin_handler_error_total",
        "Plugin handler errors",
        ["hook", "plugin", "error_type"],
    )
    PLUGIN_VOTING_DECISION = Counter(
        "stigmem_plugin_voting_decision_total",
        "Plugin voting hook decisions",
        ["hook", "decision"],
    )
    PLUGIN_REGISTRATION = Counter(
        "stigmem_plugin_registration_total",
        "Plugin registration attempts",
        ["outcome", "reason"],
    )

    # ----- Histograms -----
    REQUEST_LATENCY = Histogram(
        "stigmem_request_latency_seconds",
        "End-to-end HTTP request latency",
        ["route", "method", "status_code"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    )
    RECALL_RANKER_DURATION = Histogram(
        "stigmem_recall_ranker_duration_seconds",
        "Time spent in the hybrid recall ranker",
        ["tenant"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    )
    CAPABILITY_VERIFY_DURATION = Histogram(
        "stigmem_capability_verify_duration_seconds",
        "Time spent verifying capability tokens",
        ["result"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
    )
    PLUGIN_HOOK_DURATION = Histogram(
        "stigmem_plugin_hook_duration_seconds",
        "Plugin hook dispatch duration",
        ["hook"],
        buckets=(0.000005, 0.00001, 0.000025, 0.00005, 0.0001, 0.00025, 0.0005, 0.001),
    )
    PLUGIN_HANDLER_DURATION = Histogram(
        "stigmem_plugin_handler_duration_seconds",
        "Plugin handler invocation duration",
        ["hook", "plugin"],
        buckets=(0.000005, 0.00001, 0.000025, 0.00005, 0.0001, 0.00025, 0.0005, 0.001),
    )

    # ----- Gauges -----
    SUBSCRIPTION_CONNECTIONS = Gauge(
        "stigmem_subscription_connections_active",
        "Number of active (non-circuit-open) subscriptions",
        ["tenant"],
    )
    REPLICATION_LAG = Gauge(
        "stigmem_replication_lag_seconds",
        "Estimated replication lag to each federation peer (seconds)",
        ["peer_id"],
    )
    PLUGIN_REGISTERED_COUNT = Gauge(
        "stigmem_plugin_registered_count",
        "Number of registered plugins",
    )
    PLUGIN_HANDLERS_PER_HOOK = Gauge(
        "stigmem_plugin_handlers_per_hook",
        "Number of registered handlers per plugin hook",
        ["hook"],
    )

except ImportError:
    _ENABLED = False

    class _Noop:
        def labels(self, **_: Any) -> _Noop:
            return self

        def inc(self, amount: float = 1) -> None:
            pass

        def observe(self, amount: float) -> None:
            pass

        def set(self, value: float) -> None:
            pass

        def inc_gauge(self, amount: float = 1) -> None:
            pass

        def dec(self, amount: float = 1) -> None:
            pass

    _noop = _Noop()

    # Counters
    FACT_WRITE = _noop
    FACT_READ = _noop
    QUOTA_BREACH = _noop
    AUDIT_EVENT = _noop
    CONTRADICTION = _noop
    FEDERATION_INGRESS = _noop
    FEDERATION_EGRESS = _noop
    SUBSCRIPTION_EVENT = _noop
    PLUGIN_HOOK_FIRE = _noop
    PLUGIN_HANDLER_INVOCATION = _noop
    PLUGIN_HANDLER_ERROR = _noop
    PLUGIN_VOTING_DECISION = _noop
    PLUGIN_REGISTRATION = _noop

    # Histograms
    REQUEST_LATENCY = _noop
    RECALL_RANKER_DURATION = _noop
    CAPABILITY_VERIFY_DURATION = _noop
    PLUGIN_HOOK_DURATION = _noop
    PLUGIN_HANDLER_DURATION = _noop

    # Gauges
    SUBSCRIPTION_CONNECTIONS = _noop
    REPLICATION_LAG = _noop
    PLUGIN_REGISTERED_COUNT = _noop
    PLUGIN_HANDLERS_PER_HOOK = _noop


def metrics_enabled() -> bool:
    return _ENABLED


def make_metrics_response() -> Response | None:
    """Return a Starlette ``Response`` with the Prometheus text exposition."""
    if not _ENABLED:
        return None
    from starlette.responses import Response

    return Response(
        content=_prom.generate_latest(),
        media_type=_prom.CONTENT_TYPE_LATEST,
    )


@contextmanager
def observe_duration(histogram: Any, labels: dict[str, str]) -> Generator[None, None, None]:
    """Context manager: observe elapsed time in ``histogram`` after the block exits."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        with contextlib.suppress(Exception):  # nosec B110 — metrics best-effort
            histogram.labels(**labels).observe(elapsed)
