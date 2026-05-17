"""Compatibility alias for :mod:`stigmem_node.observability.metrics`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

__all__ = [
    "AUDIT_EVENT",
    "CAPABILITY_VERIFY_DURATION",
    "CONTRADICTION",
    "Counter",
    "FACT_READ",
    "FACT_WRITE",
    "FEDERATION_EGRESS",
    "FEDERATION_INGRESS",
    "Gauge",
    "Histogram",
    "PEER_HLC_ANOMALY",
    "PLUGIN_HANDLER_DURATION",
    "PLUGIN_HANDLER_ERROR",
    "PLUGIN_HANDLER_INVOCATION",
    "PLUGIN_HANDLERS_PER_HOOK",
    "PLUGIN_HOOK_DURATION",
    "PLUGIN_HOOK_FIRE",
    "PLUGIN_REGISTERED_COUNT",
    "PLUGIN_REGISTRATION",
    "PLUGIN_VOTING_DECISION",
    "QUOTA_BREACH",
    "RECALL_RANKER_DURATION",
    "REGISTRY",
    "REPLICATION_LAG",
    "REQUEST_LATENCY",
    "SUBSCRIPTION_CONNECTIONS",
    "SUBSCRIPTION_EVENT",
    "make_metrics_response",
    "metrics_enabled",
    "observe_duration",
]

if TYPE_CHECKING:
    from .observability.metrics import (
        AUDIT_EVENT,
        CAPABILITY_VERIFY_DURATION,
        CONTRADICTION,
        FACT_READ,
        FACT_WRITE,
        FEDERATION_EGRESS,
        FEDERATION_INGRESS,
        PEER_HLC_ANOMALY,
        PLUGIN_HANDLER_DURATION,
        PLUGIN_HANDLER_ERROR,
        PLUGIN_HANDLER_INVOCATION,
        PLUGIN_HANDLERS_PER_HOOK,
        PLUGIN_HOOK_DURATION,
        PLUGIN_HOOK_FIRE,
        PLUGIN_REGISTERED_COUNT,
        PLUGIN_REGISTRATION,
        PLUGIN_VOTING_DECISION,
        QUOTA_BREACH,
        RECALL_RANKER_DURATION,
        REPLICATION_LAG,
        REQUEST_LATENCY,
        SUBSCRIPTION_CONNECTIONS,
        SUBSCRIPTION_EVENT,
        make_metrics_response,
        metrics_enabled,
        observe_duration,
    )

    REGISTRY: Any
    Counter: Any
    Gauge: Any
    Histogram: Any
else:
    from .observability import metrics as _impl

    sys.modules[__name__] = _impl
