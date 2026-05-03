---
id: federation-4node
title: 4-Node Federation Topology
sidebar_label: 4-Node Topology
---

# 4-Node Federation Topology

**Audience:** Node operators and federation architects deploying multi-node stigmem clusters for production or soak testing.

## Overview

The stigmem reference node ships with a full-mesh 4-node Docker Compose topology for soak testing, failure-mode verification, and topology experimentation. Four nodes (`node-a` through `node-d`) form a full-mesh pull graph: every node pulls from every other, giving maximum replication coverage.

```
    node-a (8765)
   ↗    ↖       ↘
node-d   node-b (8766)
(8768)↘  ↗       ↗
    node-c (8767)
```

This topology was validated in a 72-hour soak run that included partition injection, network delay, and node restart scenarios.

## Starting the 4-node cluster

```bash
cd stigmem/infra
docker compose -f docker-compose.soak.yml up --build -d
```

Wait for all four nodes to report healthy:

```bash
docker compose -f docker-compose.soak.yml ps
```

All four services should show `healthy`:

```
NAME              STATUS          PORTS
soak-node-a-1     healthy         0.0.0.0:8765->8765/tcp
soak-node-b-1     healthy         0.0.0.0:8766->8765/tcp
soak-node-c-1     healthy         0.0.0.0:8767->8765/tcp
soak-node-d-1     healthy         0.0.0.0:8768->8765/tcp
```

## Wiring the peer mesh

The `infra/soak/setup_peers.py` script registers all 12 directed peer links (each of the 4 nodes registers with each of the 3 others) and creates federate API keys:

```bash
docker compose -f docker-compose.soak.yml exec node-a python /soak/setup_peers.py
```

This script:
1. Generates Ed25519 keypairs if not already present (via `infra/soak/keys.py`)
2. For each directed pair, POSTs a signed `PeerDeclaration` to the remote node's `/v1/federation/peers`
3. Verifies each registration returns `"status": "active"`

After setup, each node shows 3 peers:

```bash
curl -s http://localhost:8765/v1/federation/peers | jq '[.peers[] | {node_id, status}]'
```

## Seed workload

To validate replication under realistic load, use the included seed script:

```bash
docker compose -f docker-compose.soak.yml exec node-a python /soak/seed.py
```

The seed script continuously emits:
- **Probe facts** (public, no expiry): 1 per node per 30 s for replication latency measurement
- **Steady-state churn**: rotating entity states with mixed TTLs
- **Deliberate contradictions**: paired assertions from two nodes every 60 s
- **Local-scope facts**: `scope=local` — verify these never cross node boundaries
- **Conflict storms**: 50-fact burst every 10 minutes

## Failure injection

The `run_soak.sh` script orchestrates a 72-hour run with scheduled failure injection:

| Time | Failure | Duration | What to observe |
|------|---------|----------|-----------------|
| T+4h | node-c network partition | 5 min | Replication pause; contradiction storm on reconnect |
| T+24h | node-b 500ms network delay | 15 min | Backpressure header on downstream peers |
| T+48h | node-d container restart | — | Cursor-resume: no facts skipped after restart |

Run it:

```bash
bash infra/soak/run_soak.sh
```

Results are written to `infra/soak/metrics/`:
- `replication_latency.csv` — p50/p90/p99 per probe fact
- `conflict_counts.csv` — contradiction detection and convergence
- `resources.csv` — CPU/memory per node
- `local_isolation.csv` — invariant violation detector (target: 0)

## Failure modes: observed behaviors

### FM-1: Node partition (network isolation)

A partitioned node backs off its pull loop exponentially (1 s → 2 s → … → 300 s max). Facts asserted during partition accumulate locally.

On reconnect, the pull loop resumes from the last committed HLC cursor — no facts are skipped. Cross-partition contradictions are detected at ingest and stored as first-class `ConflictRecord`s. **No data is lost; no silent overwrites.**

```
Recovery time ≈ O(facts_accumulated × pull_batch_size / pull_interval_s)
```

### FM-2: Slow peer (high RTT)

At 500 ms RTT, pull succeeds but at reduced throughput. At RTT > 30 s, the pull request times out; the pull retries next cycle with the unchanged cursor. No facts lost.

For multi-hop topologies, the lagging node will emit `X-Stigmem-Replication-Lag` headers on its pull responses once lag exceeds 60 s — see the [relay backpressure guide](./relay-backpressure).

### FM-3: Node restart

Verified in `TestCursorResume::test_node_restart_resumes_without_gaps`:
- Node reads `replication_cursors` from SQLite on startup (persisted via WAL)
- Pull loop resumes from last committed cursor per peer
- Restart-to-healthy: < 5 s
- Idempotent ingest: re-delivered facts (same fact ID) are silently discarded

If the DB is lost, see the [cursor-reset recovery guide](./cursor-reset-recovery) for the `stigmem federation cursor-export / cursor-import` runbook.

### FM-4: Contradiction storm

Under burst write conditions, each ingested contradiction generates two system facts (`stigmem:conflict:between`, `stigmem:conflict:status`). These use the `stigmem:` prefix and are **not** re-replicated. At 50 contradictions/s, the HLC counter increments rapidly but remains monotonically correct per spec §2.4.

**Current limitation:** `conflicts` table has no TTL or eviction. Sustained storms will grow it unboundedly. A conflict archival policy is planned for a future spec version.

### FM-5: Malformed or expired peer token

The pull endpoint returns HTTP 401 for expired, invalid-signature, or replayed-nonce tokens. An `event_type="rejected_token"` or `"replay_attempt"` entry is written to the federation audit log. The caller retains its cursor and retries next cycle.

### FM-6: Scope boundary violation

Peers can only pull facts for scopes declared in their `PeerDeclaration`, regardless of token claims. `local`-scope facts never leave origin (spec §6.4, verified: `TestScopeIsolation`). Violations are rejected with HTTP 403 and logged as `event_type="scope_violation"`.

See the [scope propagation guide](./scope-propagation) for `company`-scoped re-federation restrictions (§6.8).

## Teardown

```bash
docker compose -f docker-compose.soak.yml down -v
```

The `-v` flag removes data volumes so the next run starts from a clean state.

## See also

- [Quickstart](../getting-started/quickstart) — two-node setup in under 10 minutes
- [Federation guide](./federation) — PeerDeclaration registration, cursor behavior, and audit log
- [Relay backpressure](./relay-backpressure) — lag signals in N-node topologies (§6.7)
- [Scope propagation](./scope-propagation) — scope invariants across relay hops (§6.8)
- Spec §6 — Federation protocol
