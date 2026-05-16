"""Thread-safe metrics state for the federation soak harness."""

from __future__ import annotations

import math
import threading

_lock = threading.Lock()
_lag_samples_ab: list[float] = []
_lag_samples_ac: list[float] = []
_probe_count = 0
_cap_token_total = 0
_cap_token_verified = 0
_audit_facts_sent = 0
_audit_facts_received = 0


def increment_probe_count() -> int:
    global _probe_count, _audit_facts_sent
    with _lock:
        _probe_count += 1
        _audit_facts_sent += 1
        return _probe_count


def increment_audit_facts_received() -> None:
    global _audit_facts_received
    with _lock:
        _audit_facts_received += 1


def increment_cap_token_total() -> None:
    global _cap_token_total
    with _lock:
        _cap_token_total += 1


def increment_cap_token_verified() -> None:
    global _cap_token_verified
    with _lock:
        _cap_token_verified += 1


def get_probe_count() -> int:
    with _lock:
        return _probe_count


def snapshot() -> dict:
    with _lock:
        return {
            "lag_samples_ab": list(_lag_samples_ab),
            "lag_samples_ac": list(_lag_samples_ac),
            "cap_token_total": _cap_token_total,
            "cap_token_verified": _cap_token_verified,
            "audit_facts_sent": _audit_facts_sent,
            "audit_facts_received": _audit_facts_received,
        }


def _percentile(samples: list[float], pct: float) -> float:
    if not samples:
        return 0.0
    s = sorted(samples)
    idx = min(int(math.ceil(pct / 100.0 * len(s))) - 1, len(s) - 1)
    return s[max(0, idx)]


def _histogram_buckets(samples: list[float]) -> list[dict]:
    boundaries = [100, 500, 1000, 2000, 5000, 10000]
    buckets: list[dict] = []
    for bound in boundaries:
        count = sum(1 for s in samples if s <= bound)
        buckets.append({"le_ms": bound, "count": count})
    buckets.append({"le_ms": None, "count": len(samples)})  # +Inf
    return buckets


def _record_lag(target_node: str, lag_ms: float) -> None:
    global _lag_samples_ab, _lag_samples_ac
    with _lock:
        if target_node == "node-b":
            _lag_samples_ab.append(lag_ms)
        else:
            _lag_samples_ac.append(lag_ms)
