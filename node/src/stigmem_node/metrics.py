"""Optional Prometheus metrics for the Stigmem reference node — spec §22.4.

If ``prometheus_client`` is installed, this module registers counters and
exposes them via ``/metrics``.  If the package is absent, all operations
are no-ops so the node runs without the dependency.

Counters registered:
  stigmem_fact_write_total{principal, tenant}
  stigmem_fact_read_total{principal, tenant}
  stigmem_quota_breach_total{principal, tenant, dimension}
  stigmem_audit_event_total{event_type, tenant}
"""

from __future__ import annotations

from typing import Any

try:
    import prometheus_client as _prom
    from prometheus_client import Counter, REGISTRY  # noqa: F401

    _ENABLED = True

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
        "Total audit events emitted",
        ["event_type", "tenant"],
    )

except ImportError:
    _ENABLED = False

    class _Noop:
        def labels(self, **_: Any) -> "_Noop":
            return self
        def inc(self, amount: float = 1) -> None:
            pass

    _noop = _Noop()
    FACT_WRITE = _noop  # type: ignore[assignment]
    FACT_READ = _noop   # type: ignore[assignment]
    QUOTA_BREACH = _noop  # type: ignore[assignment]
    AUDIT_EVENT = _noop   # type: ignore[assignment]


def metrics_enabled() -> bool:
    return _ENABLED


def make_metrics_response() -> Any:
    """Return a Starlette ``Response`` with the Prometheus text exposition."""
    if not _ENABLED:
        return None
    from starlette.responses import Response
    return Response(
        content=_prom.generate_latest(),
        media_type=_prom.CONTENT_TYPE_LATEST,
    )
