"""Workload run phase for the federation soak harness."""

from __future__ import annotations

import time
import uuid

import httpx

from . import state as metrics
from .monitor import _assert_fact, _probe_replication, _verify_cap_token, check_audit_completeness
from .scenarios import run_cc1, run_cc2, run_cc3, run_cc4, run_cc5


def run_workload(
    clients: dict[str, httpx.Client],
    admin_keys: dict[str, str],
    duration_s: float,
    smoke: bool,
) -> dict:
    """
    Drive assert/query/recall workload and collect metrics.
    Returns a dict with all scenario results and metric samples.
    """
    tracked_probe_ids: list[str] = []
    cc_results: list[dict] = []

    warmup_s = 60.0 if not smoke else 15.0
    print(f"→ Warmup ({warmup_s:.0f} s)…")
    warmup_end = time.monotonic() + warmup_s

    warmup_probes: list[str] = []
    while time.monotonic() < warmup_end:
        entity = f"stigmem://eval/warmup/{uuid.uuid4()}"
        fid = _assert_fact(clients["node-a"], entity, "eval:warmup", str(uuid.uuid4()))
        if fid:
            warmup_probes.append(fid)
        # Also assert on B and C to populate both directions
        _assert_fact(
            clients["node-b"],
            f"stigmem://eval/warmup-b/{uuid.uuid4()}",
            "eval:warmup",
            str(uuid.uuid4()),
        )
        time.sleep(2.0)

    print(f"→ Steady-state workload ({duration_s:.0f} s)…")

    # Schedule conflict scenarios spread across the run (smoke: every 30 s from T+30)
    scenario_fns = [run_cc1, run_cc2, run_cc3, run_cc4]
    if smoke:
        cc_schedule = [30.0 + i * 30.0 for i in range(4)]
        cc5_at = 155.0
    else:
        cc_schedule = [120.0, 300.0, 600.0, 900.0]
        cc5_at = 1200.0

    run_start = time.monotonic()
    run_end = run_start + duration_s

    scenario_idx = 0
    cc5_done = False

    while time.monotonic() < run_end:
        elapsed = time.monotonic() - run_start

        # Inject scheduled CC scenarios
        if scenario_idx < len(cc_schedule) and elapsed >= cc_schedule[scenario_idx]:
            fn = scenario_fns[scenario_idx]
            print(f"  [{elapsed:.0f} s] Running {fn.__name__}…")
            result = fn(clients)
            cc_results.append(result)
            print(
                f"  {fn.__name__}: {'PASS' if result['passed'] else 'FAIL'} "
                f"(conv={result['convergence_s']:.1f} s)"
            )
            scenario_idx += 1

        if not cc5_done and elapsed >= cc5_at:
            print(f"  [{elapsed:.0f} s] Running run_cc5…")
            result = run_cc5(clients, admin_keys)
            cc_results.append(result)
            cc5_done = True
            print(f"  run_cc5: {'PASS' if result['passed'] else 'FAIL'}")

        # Probe replication — asserts on node-A and measures propagation to B/C
        probe_id = _probe_replication(clients["node-a"], clients)
        if probe_id:
            tracked_probe_ids.append(probe_id)

        # Cross-node capability-token verification probe (every ~10 probes)
        if metrics.get_probe_count() % 10 == 1 and probe_id:
            _verify_cap_token(clients["node-a"], probe_id, admin_keys["node-a"])

        # Mixed steady-state: also assert on B and C
        _assert_fact(
            clients["node-b"], f"stigmem://eval/b/{uuid.uuid4()}", "eval:steady", str(uuid.uuid4())
        )
        _assert_fact(
            clients["node-c"], f"stigmem://eval/c/{uuid.uuid4()}", "eval:steady", str(uuid.uuid4())
        )

        time.sleep(3.0)

    # Wait for any remaining propagation (up to 30 s)
    print("→ Waiting for final propagation (30 s)…")
    time.sleep(30.0)

    # Audit completeness uses the probe facts tracked by _probe_replication().
    # Also spot-check a sample of recent probes on node-B for belt-and-suspenders.
    audit_completeness = check_audit_completeness(clients, tracked_probe_ids[:50])
    metrics_snapshot = metrics.snapshot()

    return {
        "cc_results": cc_results,
        "audit_completeness": audit_completeness,
        "audit_facts_sent": metrics_snapshot["audit_facts_sent"],
        "audit_facts_received": metrics_snapshot["audit_facts_received"],
        "tracked_probe_count": len(tracked_probe_ids),
    }
