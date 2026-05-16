"""Report artifact generation for the federation soak harness."""

from __future__ import annotations

import json
from pathlib import Path

from . import state as metrics
from .constants import LAG_FAIL_MS, LAG_WARN_MS, RESULTS_DIR


def build_artifact(
    run_date: str,
    duration_s: float,
    workload: dict,
    smoke: bool,
) -> dict:
    metrics_snapshot = metrics.snapshot()
    ab = metrics_snapshot["lag_samples_ab"]
    ac = metrics_snapshot["lag_samples_ac"]
    cap_total = metrics_snapshot["cap_token_total"]
    cap_verified = metrics_snapshot["cap_token_verified"]

    token_rate = cap_verified / cap_total if cap_total else 1.0
    audit_completeness = workload["audit_completeness"]

    cc_list = workload["cc_results"]
    overall_pass = (
        all(r["passed"] for r in cc_list)
        and token_rate >= 1.0
        and audit_completeness >= 1.0
        and (metrics._percentile(ab, 99) <= LAG_FAIL_MS if ab else True)
        and (metrics._percentile(ac, 99) <= LAG_FAIL_MS if ac else True)
    )

    return {
        "run_date": run_date,
        "duration_s": int(duration_s),
        "smoke": smoke,
        "replication_lag": {
            "node_a_to_b": {
                "p50_ms": round(metrics._percentile(ab, 50), 1),
                "p95_ms": round(metrics._percentile(ab, 95), 1),
                "p99_ms": round(metrics._percentile(ab, 99), 1),
                "buckets": metrics._histogram_buckets(ab),
                "sample_count": len(ab),
            },
            "node_a_to_c": {
                "p50_ms": round(metrics._percentile(ac, 50), 1),
                "p95_ms": round(metrics._percentile(ac, 95), 1),
                "p99_ms": round(metrics._percentile(ac, 99), 1),
                "buckets": metrics._histogram_buckets(ac),
                "sample_count": len(ac),
            },
        },
        "token_verification_rate": round(token_rate, 6),
        "audit_completeness": round(audit_completeness, 6),
        "conflict_convergence": [
            {
                "scenario": r["scenario"],
                "passed": r["passed"],
                "convergence_s": r["convergence_s"],
            }
            for r in cc_list
        ],
        "overall_pass": overall_pass,
    }


def write_artifacts(artifact: dict, date_str: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / f"soak-{date_str}.json"
    md_path = RESULTS_DIR / f"soak-{date_str}.md"

    json_path.write_text(json.dumps(artifact, indent=2) + "\n")

    lag_ab = artifact["replication_lag"]["node_a_to_b"]
    lag_ac = artifact["replication_lag"]["node_a_to_c"]

    cc_table = "\n".join(
        f"| {r['scenario']} | {'✓' if r['passed'] else '✗'} | {r['convergence_s']:.1f} |"
        for r in artifact["conflict_convergence"]
    )

    status = "PASS ✓" if artifact["overall_pass"] else "FAIL ✗"
    md_path.write_text(f"""\
# Federation Soak Report

**Run date:** {artifact["run_date"]}
**Duration:** {artifact["duration_s"]} s (smoke={artifact["smoke"]})
**Overall:** {status}

## Replication Lag

| Node pair | P50 ms | P95 ms | P99 ms | Samples |
|-----------|--------|--------|--------|---------|
| A → B | {lag_ab["p50_ms"]} | {lag_ab["p95_ms"]} | {lag_ab["p99_ms"]} | {lag_ab["sample_count"]} |
| A → C | {lag_ac["p50_ms"]} | {lag_ac["p95_ms"]} | {lag_ac["p99_ms"]} | {lag_ac["sample_count"]} |

Thresholds: P99 > {LAG_WARN_MS} ms = warning; P99 > {LAG_FAIL_MS} ms = failure.

## Security Metrics

| Metric | Value | Threshold |
|--------|-------|-----------|
| Token verification rate | {artifact["token_verification_rate"]:.4f} | 1.0 |
| Audit completeness | {artifact["audit_completeness"]:.4f} | 1.0 |

## Conflict Convergence

| Scenario | Passed | Convergence (s) |
|----------|--------|-----------------|
{cc_table}
""")

    return json_path, md_path
