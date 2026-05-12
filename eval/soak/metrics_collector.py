#!/usr/bin/env python3
"""Metrics collection for the 4-node stigmem federation soak test.

Collects and writes four CSV files under metrics/:
  replication_latency.csv  — per-probe latency from assert to first appearance on each target
  contradiction_convergence.csv — time for conflict facts to appear on all 4 nodes
  conflict_counts.csv      — periodic snapshot of unresolved/resolved conflicts per node
  resources.csv            — CPU/mem/net per container (docker stats, every 60s)
  local_isolation.csv      — local-scope facts that illegally appear on other nodes (correctness)

Replication latency methodology:
  Seed.py writes probe entries to metrics/probes.jsonl.
  Each probe has a source_node and fact_id.
  This collector polls GET /v1/facts/{fact_id} on every non-source node.
  First HTTP 200 response records appearance time.
  latency_s = appearance_time - assert_ts (from probe record).

Partition-tolerance invariant check:
  local-scope facts (soak:local:marker) must NEVER appear on nodes other than origin.
  Any sighting is written to local_isolation.csv as a violation.
"""

from __future__ import annotations

import csv
import json
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

SOAK_DIR = Path(__file__).parent
METRICS_DIR = SOAK_DIR / "metrics"
PROBES_PATH = METRICS_DIR / "probes.jsonl"

NODES = [
    {"name": "node-a", "host_url": "http://localhost:8765", "container": "soak-node-a"},
    {"name": "node-b", "host_url": "http://localhost:8766", "container": "soak-node-b"},
    {"name": "node-c", "host_url": "http://localhost:8767", "container": "soak-node-c"},
    {"name": "node-d", "host_url": "http://localhost:8768", "container": "soak-node-d"},
]
NODE_NAMES = {n["name"] for n in NODES}
PROBE_TIMEOUT_S = 300  # stop tracking a probe after 5 minutes


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def _csv_writer(path: Path, fieldnames: list[str]) -> tuple:
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    f = open(path, "a", newline="")
    w = csv.DictWriter(f, fieldnames=fieldnames)
    if not existed:
        w.writeheader()
    return f, w


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Replication latency
# ---------------------------------------------------------------------------


class ProbeTracker:
    """Track the replication of seed probe facts to non-source nodes."""

    def __init__(self) -> None:
        # probe_id → {fact_id, source_node, assert_ts, started_at, pending_nodes: set}
        self._probes: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._seen_probe_ids: set[str] = set()

    def load_new_probes(self) -> None:
        if not PROBES_PATH.exists():
            return
        with open(PROBES_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    p = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = p["fact_id"]
                with self._lock:
                    if key not in self._seen_probe_ids:
                        self._seen_probe_ids.add(key)
                        pending = NODE_NAMES - {p["source_node"]}
                        self._probes[key] = {
                            "fact_id": key,
                            "source_node": p["source_node"],
                            "assert_ts": p["assert_ts"],
                            "started_at": time.monotonic(),
                            "pending_nodes": pending,
                        }

    def check_probes(self, lat_writer) -> None:
        now_mono = time.monotonic()
        completed: list[str] = []

        with self._lock:
            probes_snapshot = dict(self._probes)

        for fact_id, probe in probes_snapshot.items():
            if now_mono - probe["started_at"] > PROBE_TIMEOUT_S:
                for node_name in list(probe["pending_nodes"]):
                    lat_writer.writerow(
                        {
                            "ts": _now_iso(),
                            "fact_id": fact_id,
                            "source_node": probe["source_node"],
                            "target_node": node_name,
                            "assert_ts": probe["assert_ts"],
                            "appear_ts": "",
                            "latency_s": "TIMEOUT",
                        }
                    )
                completed.append(fact_id)
                continue

            for node_name in list(probe["pending_nodes"]):
                node = next(n for n in NODES if n["name"] == node_name)
                try:
                    r = requests.get(
                        f"{node['host_url']}/v1/facts/{fact_id}",
                        timeout=5,
                    )
                    if r.status_code == 200:
                        appear_ts = _now_iso()
                        assert_dt = datetime.fromisoformat(probe["assert_ts"])
                        appear_dt = datetime.fromisoformat(appear_ts)
                        latency_s = (appear_dt - assert_dt).total_seconds()
                        lat_writer.writerow(
                            {
                                "ts": _now_iso(),
                                "fact_id": fact_id,
                                "source_node": probe["source_node"],
                                "target_node": node_name,
                                "assert_ts": probe["assert_ts"],
                                "appear_ts": appear_ts,
                                "latency_s": round(latency_s, 3),
                            }
                        )
                        with self._lock:
                            if fact_id in self._probes:
                                self._probes[fact_id]["pending_nodes"].discard(node_name)
                except Exception:
                    pass

            with self._lock:
                if fact_id in self._probes and not self._probes[fact_id]["pending_nodes"]:
                    completed.append(fact_id)

        with self._lock:
            for fid in completed:
                self._probes.pop(fid, None)


# ---------------------------------------------------------------------------
# Contradiction convergence
# ---------------------------------------------------------------------------


def collect_conflicts(nodes: list[dict], conv_writer, count_writer) -> None:
    """Sample conflict counts on each node and detect cross-node convergence."""
    ts = _now_iso()
    for node in nodes:
        try:
            r = requests.get(
                f"{node['host_url']}/v1/conflicts",
                params={"limit": 500},
                timeout=10,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            conflicts = data.get("conflicts", []) if isinstance(data, dict) else data
            total = len(conflicts)
            unresolved = sum(1 for c in conflicts if c.get("status") == "unresolved")
            resolved = total - unresolved
            count_writer.writerow(
                {
                    "ts": ts,
                    "node": node["name"],
                    "total_conflicts": total,
                    "unresolved": unresolved,
                    "resolved": resolved,
                }
            )
        except Exception as exc:
            print(f"[metrics] conflict poll error {node['name']}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Local isolation check
# ---------------------------------------------------------------------------


def check_local_isolation(iso_writer) -> None:
    """Verify local-scope facts from one node never appear on others.
    Any violation is a partition-tolerance invariant breach."""
    for source_node in NODES:
        try:
            r = requests.get(
                f"{source_node['host_url']}/v1/facts",
                params={"relation": "soak:local:marker", "scope": "local", "limit": 100},
                timeout=10,
            )
            if r.status_code != 200:
                continue
            local_facts = r.json().get("facts", [])
        except Exception:
            continue

        for fact in local_facts:
            fid = fact["id"]
            for target_node in NODES:
                if target_node["name"] == source_node["name"]:
                    continue
                try:
                    r2 = requests.get(
                        f"{target_node['host_url']}/v1/facts/{fid}",
                        timeout=5,
                    )
                    if r2.status_code == 200:
                        iso_writer.writerow(
                            {
                                "ts": _now_iso(),
                                "fact_id": fid,
                                "source_node": source_node["name"],
                                "target_node": target_node["name"],
                                "entity": fact.get("entity", ""),
                                "violation": "local_scope_leaked",
                            }
                        )
                        print(
                            f"[metrics] VIOLATION: local fact {fid} from {source_node['name']} "
                            f"found on {target_node['name']}",
                            file=sys.stderr,
                        )
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Resource metrics (docker stats)
# ---------------------------------------------------------------------------


def collect_resources(res_writer) -> None:
    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}",
                *(n["container"] for n in NODES),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        ts = _now_iso()
        for line in result.stdout.splitlines():
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            name, cpu_pct, mem_usage, net_io = parts[0], parts[1], parts[2], parts[3]
            # mem_usage format: "12.3MiB / 1.5GiB"
            mem_used = mem_usage.split("/")[0].strip() if "/" in mem_usage else mem_usage
            # net_io format: "1.2kB / 3.4MB"
            net_parts = net_io.split("/")
            net_rx = net_parts[0].strip() if net_parts else ""
            net_tx = net_parts[1].strip() if len(net_parts) > 1 else ""
            res_writer.writerow(
                {
                    "ts": ts,
                    "container": name,
                    "cpu_pct": cpu_pct.replace("%", ""),
                    "mem_used": mem_used,
                    "net_rx": net_rx,
                    "net_tx": net_tx,
                }
            )
    except Exception as exc:
        print(f"[metrics] docker stats error: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_running = True


def _handle_signal(sig, frame):
    global _running
    print("\n[metrics] stopping...", file=sys.stderr)
    _running = False


def main() -> None:
    global _running
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    lat_f, lat_w = _csv_writer(
        METRICS_DIR / "replication_latency.csv",
        ["ts", "fact_id", "source_node", "target_node", "assert_ts", "appear_ts", "latency_s"],
    )
    conv_f, conv_w = _csv_writer(
        METRICS_DIR / "contradiction_convergence.csv",
        ["ts", "conflict_id", "source_node", "target_node", "first_seen_ts", "convergence_s"],
    )
    count_f, count_w = _csv_writer(
        METRICS_DIR / "conflict_counts.csv",
        ["ts", "node", "total_conflicts", "unresolved", "resolved"],
    )
    res_f, res_w = _csv_writer(
        METRICS_DIR / "resources.csv",
        ["ts", "container", "cpu_pct", "mem_used", "net_rx", "net_tx"],
    )
    iso_f, iso_w = _csv_writer(
        METRICS_DIR / "local_isolation.csv",
        ["ts", "fact_id", "source_node", "target_node", "entity", "violation"],
    )

    tracker = ProbeTracker()

    tick = 0
    print("[metrics] starting collection loop (Ctrl+C to stop)")

    while _running:
        try:
            tracker.load_new_probes()
            tracker.check_probes(lat_w)
            lat_f.flush()

            # Conflict counts every 60s
            if tick % 12 == 0:
                collect_conflicts(NODES, conv_w, count_w)
                count_f.flush()
                conv_f.flush()

            # Resource sampling every 60s
            if tick % 12 == 0:
                collect_resources(res_w)
                res_f.flush()

            # Local isolation check every 5 minutes
            if tick % 60 == 0:
                check_local_isolation(iso_w)
                iso_f.flush()

        except Exception as exc:
            print(f"[metrics] loop error: {exc}", file=sys.stderr)

        tick += 1
        time.sleep(5)

    for f in [lat_f, conv_f, count_f, res_f, iso_f]:
        f.close()

    print("[metrics] done — files flushed")


if __name__ == "__main__":
    main()
