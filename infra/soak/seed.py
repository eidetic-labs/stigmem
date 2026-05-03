#!/usr/bin/env python3
"""Continuous fact seeding for the 4-node stigmem federation soak test.

Runs forever until interrupted (SIGINT/SIGTERM). Writes probe metadata to
metrics/probes.jsonl so metrics_collector.py can track replication latency.

Seed patterns (all using public scope unless noted):
  - Probe facts: 1 per node every 30s (unique entity/uuid → measures latency)
  - Steady-state: rotate values on shared entities (generates churn + occasional conflicts)
  - Deliberate contradictions: same entity asserted from two different nodes
  - Expiry variants: short (90s), medium (30min), long (24h), no-expiry
  - Local-only facts: scope=local (verify these never federate to other nodes)

CAP lens: public facts choose availability over consistency; contradictions are
first-class observable events, not error cases (conflict-first-class design).
"""

from __future__ import annotations

import json
import os
import random
import signal
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

SOAK_DIR = Path(__file__).parent
METRICS_DIR = SOAK_DIR / "metrics"
FEDERATE_KEYS_PATH = SOAK_DIR / "federate_keys.json"
PROBES_PATH = METRICS_DIR / "probes.jsonl"

NODES = [
    {"name": "node-a", "host_url": "http://localhost:8765"},
    {"name": "node-b", "host_url": "http://localhost:8766"},
    {"name": "node-c", "host_url": "http://localhost:8767"},
    {"name": "node-d", "host_url": "http://localhost:8768"},
]

# Expiry windows used in rotation
_EXPIRY_WINDOWS = [
    None,                # no expiry
    timedelta(seconds=90),
    timedelta(minutes=30),
    timedelta(hours=24),
]

# Deliberate contradiction pairs (same entity, different source nodes)
_CONFLICT_ENTITIES = [f"soak://conflict/target-{i}" for i in range(20)]
_CONFLICT_VALUES = [
    ["red", "blue"],
    ["on", "off"],
    ["high", "low"],
    ["alpha", "beta"],
    ["enabled", "disabled"],
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _expiry(window: timedelta | None) -> str | None:
    if window is None:
        return None
    return (datetime.now(UTC) + window).isoformat()


def _assert_fact(
    host_url: str,
    entity: str,
    relation: str,
    value: object,
    scope: str = "public",
    source: str = "soak:seeder",
    valid_until: str | None = None,
    confidence: float = 1.0,
    api_key: str | None = None,
) -> dict | None:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        r = requests.post(
            f"{host_url}/v1/facts",
            json={
                "entity": entity,
                "relation": relation,
                "value": {"type": "string", "v": str(value)},
                "source": source,
                "scope": scope,
                "valid_until": valid_until,
                "confidence": confidence,
            },
            headers=headers,
            timeout=10,
        )
        if r.status_code == 201:
            return r.json()
        print(f"[seed] assert failed {host_url} {r.status_code} {r.text[:80]}", file=sys.stderr)
    except Exception as exc:
        print(f"[seed] assert error {host_url}: {exc}", file=sys.stderr)
    return None


def _load_keys() -> dict[str, str | None]:
    if FEDERATE_KEYS_PATH.exists():
        with open(FEDERATE_KEYS_PATH) as f:
            return json.load(f)
    # No auth required by default; return empty (anon has read+write but not federate)
    return {n["name"]: None for n in NODES}


def _write_probe(probe: dict) -> None:
    with open(PROBES_PATH, "a") as f:
        f.write(json.dumps(probe) + "\n")


# ---------------------------------------------------------------------------
# Seed routines
# ---------------------------------------------------------------------------


def seed_probe_facts(keys: dict) -> None:
    """Assert one probe fact per node. Metrics collector tracks when each
    appears on the other 3 nodes to compute replication latency."""
    for node in NODES:
        fact_uuid = str(uuid.uuid4())
        entity = f"soak://probe/{fact_uuid}"
        assert_ts = _now_iso()
        result = _assert_fact(
            node["host_url"],
            entity=entity,
            relation="soak:probe:ts",
            value=assert_ts,
            scope="public",
            source="soak:seeder",
            api_key=keys.get(node["name"]),
        )
        if result:
            probe = {
                "fact_id": result["id"],
                "source_node": node["name"],
                "entity": entity,
                "assert_ts": assert_ts,
                "ts": _now_iso(),
            }
            _write_probe(probe)


def seed_steady_state(keys: dict, cycle: int) -> None:
    """Assert rotating values on a shared entity pool. Generates churn without
    overwhelming the contradiction detector."""
    node = NODES[cycle % len(NODES)]
    entity_n = (cycle // len(NODES)) % 100
    entity = f"soak://entity/user-{entity_n}"
    states = ["active", "idle", "busy", "offline"]
    value = states[cycle % len(states)]
    expiry = _expiry(_EXPIRY_WINDOWS[cycle % len(_EXPIRY_WINDOWS)])
    _assert_fact(
        node["host_url"],
        entity=entity,
        relation="soak:status",
        value=value,
        scope="public",
        valid_until=expiry,
        api_key=keys.get(node["name"]),
    )


def seed_contradictions(keys: dict, cycle: int) -> None:
    """Assert the same entity from two different nodes with different values.
    Both nodes assert independently; contradiction detection fires on ingest."""
    target_n = cycle % len(_CONFLICT_ENTITIES)
    entity = _CONFLICT_ENTITIES[target_n]
    values = _CONFLICT_VALUES[cycle % len(_CONFLICT_VALUES)]

    node_a = NODES[cycle % len(NODES)]
    node_b = NODES[(cycle + 1) % len(NODES)]

    for node, val in [(node_a, values[0]), (node_b, values[1])]:
        _assert_fact(
            node["host_url"],
            entity=entity,
            relation="soak:conflict:value",
            value=val,
            scope="public",
            source=f"soak:seeder:{node['name']}",
            confidence=0.9,
            api_key=keys.get(node["name"]),
        )


def seed_local_facts(keys: dict, cycle: int) -> None:
    """Assert local-scope facts on each node. These MUST NOT appear on other
    nodes. Metrics collector verifies non-replication as a correctness check."""
    node = NODES[cycle % len(NODES)]
    entity = f"soak://local/{node['name']}/probe-{cycle}"
    _assert_fact(
        node["host_url"],
        entity=entity,
        relation="soak:local:marker",
        value=f"local-{cycle}",
        scope="local",
        api_key=keys.get(node["name"]),
    )


def seed_expiry_facts(keys: dict, cycle: int) -> None:
    """Assert facts with short (90s) TTL to verify expiry propagates correctly
    and expired facts are excluded from normal query results."""
    node = NODES[cycle % len(NODES)]
    entity = f"soak://expiry/{node['name']}/{cycle}"
    _assert_fact(
        node["host_url"],
        entity=entity,
        relation="soak:expiry:check",
        value="expiring",
        scope="public",
        valid_until=_expiry(timedelta(seconds=90)),
        api_key=keys.get(node["name"]),
    )


def seed_conflict_storm(keys: dict, burst_size: int = 50) -> None:
    """Rapidly fire contradicting facts to stress-test conflict detection and
    replication convergence under high contradiction load."""
    print(f"[seed] conflict storm: {burst_size} contradictions")
    for i in range(burst_size):
        entity = f"soak://storm/entity-{i % 10}"
        node_a = NODES[i % len(NODES)]
        node_b = NODES[(i + 1) % len(NODES)]
        for node, val in [(node_a, f"storm-a-{i}"), (node_b, f"storm-b-{i}")]:
            _assert_fact(
                node["host_url"],
                entity=entity,
                relation="soak:storm:value",
                value=val,
                scope="public",
                confidence=random.uniform(0.5, 1.0),
                api_key=keys.get(node["name"]),
            )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

_running = True


def _handle_signal(sig, frame):
    global _running
    print("\n[seed] stopping...", file=sys.stderr)
    _running = False


def main() -> None:
    global _running
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    keys = _load_keys()

    print("[seed] starting continuous seed loop (Ctrl+C to stop)")
    print(f"[seed] probes → {PROBES_PATH}")

    cycle = 0
    probe_interval = 30       # seconds between probe rounds
    steady_interval = 10      # seconds between steady-state asserts
    contradiction_interval = 60  # seconds between deliberate contradictions
    local_interval = 60
    expiry_interval = 120
    conflict_storm_interval = 600  # 10 min

    last_probe = 0.0
    last_steady = 0.0
    last_contradiction = 0.0
    last_local = 0.0
    last_expiry = 0.0
    last_storm = 0.0

    while _running:
        now = time.monotonic()

        if now - last_probe >= probe_interval:
            seed_probe_facts(keys)
            last_probe = now

        if now - last_steady >= steady_interval:
            seed_steady_state(keys, cycle)
            last_steady = now

        if now - last_contradiction >= contradiction_interval:
            seed_contradictions(keys, cycle)
            last_contradiction = now

        if now - last_local >= local_interval:
            seed_local_facts(keys, cycle)
            last_local = now

        if now - last_expiry >= expiry_interval:
            seed_expiry_facts(keys, cycle)
            last_expiry = now

        if now - last_storm >= conflict_storm_interval:
            seed_conflict_storm(keys)
            last_storm = now

        cycle += 1
        time.sleep(5)

    print("[seed] done")


if __name__ == "__main__":
    main()
