---
title: 4-Node Federation Topology
sidebar_label: 4-Node Topology
audience: Integrator
---

# 4-Node Federation Topology

<p className="stigmem-meta"><span>4 min read</span><span>Node operator · Federation architect</span><span>Soak validated</span></p>

<div className="stigmem-lead">

**What this page is**

A full-mesh 4-node Docker Compose topology for soak testing,
failure-mode verification, and topology experimentation. Validated
in a 72-hour soak run with partition injection, network delay, and
node restart scenarios.

</div>

## Overview

Four nodes (`node-a` through `node-d`) form a full-mesh pull graph:
every node pulls from every other, giving maximum replication
coverage.

```
    node-a (8765)
   ↗    ↖       ↘
node-d   node-b (8766)
(8768)↘  ↗       ↗
    node-c (8767)
```

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

The `infra/soak/setup_peers.py` script registers all 12 directed peer
links (each of the 4 nodes registers with each of the 3 others) and
creates federate API keys.

```bash
docker compose -f docker-compose.soak.yml exec node-a python /soak/setup_peers.py
```

<ol className="stigmem-steps">
<li>Generates Ed25519 keypairs if not already present (via <code>infra/soak/keys.py</code>).</li>
<li>For each directed pair, POSTs a signed <code>PeerDeclaration</code> to the remote node's <code>/v1/federation/peers</code>.</li>
<li>Verifies each registration returns <code>"status": "active"</code>.</li>
</ol>

After setup, each node shows 3 peers:

```bash
curl -s http://localhost:8765/v1/federation/peers | jq '[.peers[] | {node_id, status}]'
```

## Seed workload

To validate replication under realistic load, use the included seed
script:

```bash
docker compose -f docker-compose.soak.yml exec node-a python /soak/seed.py
```

The seed script continuously emits:

<div className="stigmem-grid">

<div><h4>Probe facts</h4><p>Public, no expiry: 1 per node per 30s for replication latency measurement.</p></div>
<div><h4>Steady-state churn</h4><p>Rotating entity states with mixed TTLs.</p></div>
<div><h4>Deliberate contradictions</h4><p>Paired assertions from two nodes every 60s.</p></div>
<div><h4>Local-scope facts</h4><p><code>scope=local</code> — verify these never cross node boundaries.</p></div>
<div><h4>Conflict storms</h4><p>50-fact burst every 10 minutes.</p></div>

</div>

## Failure injection

The `run_soak.sh` script orchestrates a 72-hour run with scheduled
failure injection.

<div className="stigmem-fields">

<div>
<dt>Time</dt>
<dt><span className="stigmem-fields__type">Failure · Duration</span></dt>
<dd>What to observe</dd>
</div>

<div>
<dt>T+4h</dt>
<dt><span className="stigmem-fields__type">node-c network partition · 5 min</span></dt>
<dd>Replication pause; contradiction storm on reconnect.</dd>
</div>

<div>
<dt>T+24h</dt>
<dt><span className="stigmem-fields__type">node-b 500ms network delay · 15 min</span></dt>
<dd>Backpressure header on downstream peers.</dd>
</div>

<div>
<dt>T+48h</dt>
<dt><span className="stigmem-fields__type">node-d container restart</span></dt>
<dd>Cursor-resume: no facts skipped after restart.</dd>
</div>

</div>

Run it:

```bash
bash infra/soak/run_soak.sh
```

Results are written to `infra/soak/metrics/`:

<div className="stigmem-grid">

<div><h4><code>replication_latency.csv</code></h4><p>p50/p90/p99 per probe fact.</p></div>
<div><h4><code>conflict_counts.csv</code></h4><p>Contradiction detection and convergence.</p></div>
<div><h4><code>resources.csv</code></h4><p>CPU/memory per node.</p></div>
<div><h4><code>local_isolation.csv</code></h4><p>Invariant violation detector (target: 0).</p></div>

</div>

## Failure modes · observed behaviors

### FM-1 · Node partition (network isolation)

A partitioned node backs off its pull loop exponentially
(1s → 2s → … → 300s max). Facts asserted during partition
accumulate locally.

<div className="stigmem-keypoint">

**On reconnect, the pull loop resumes from the last committed HLC cursor — no facts are skipped.**

Cross-partition contradictions are detected at ingest and stored as
first-class <code>ConflictRecord</code>s. <strong>No data is lost; no
silent overwrites.</strong>

</div>

```
Recovery time ≈ O(facts_accumulated × pull_batch_size / pull_interval_s)
```

### FM-2 · Slow peer (high RTT)

At 500ms RTT, pull succeeds but at reduced throughput. At RTT > 30s,
the pull request times out; the pull retries next cycle with the
unchanged cursor. **No facts lost.**

For multi-hop topologies, the lagging node will emit
`X-Stigmem-Replication-Lag` headers on its pull responses once lag
exceeds 60s — see the [relay backpressure guide](./relay-backpressure).

### FM-3 · Node restart

Verified in `TestCursorResume::test_node_restart_resumes_without_gaps`.

<div className="stigmem-grid">

<div><h4>Cursor read on startup</h4><p>Node reads <code>replication_cursors</code> from SQLite on startup (persisted via WAL).</p></div>
<div><h4>Pull loop resumes</h4><p>From last committed cursor per peer.</p></div>
<div><h4>Restart-to-healthy</h4><p>&lt; 5s.</p></div>
<div><h4>Idempotent ingest</h4><p>Re-delivered facts (same fact ID) are silently discarded.</p></div>

</div>

If the DB is lost, see the
[cursor-reset recovery guide](../../operators/runbooks/cursor-reset-recovery)
for the `stigmem federation cursor-export / cursor-import` runbook.

### FM-4 · Contradiction storm

Under burst write conditions, each ingested contradiction generates
two system facts (`stigmem:conflict:between`,
`stigmem:conflict:status`). These use the `stigmem:` prefix and are
**not** re-replicated. At 50 contradictions/s, the HLC counter
increments rapidly but remains monotonically correct per
Spec-12-HLC-Bounded-Skew.

<div className="stigmem-keypoint">

**Current limitation: `conflicts` table has no TTL or eviction.**

Sustained storms will grow it unboundedly. A conflict archival policy
is planned for a future spec version.

</div>

### FM-5 · Malformed or expired peer token

The pull endpoint returns HTTP 401 for expired, invalid-signature,
or replayed-nonce tokens. An `event_type="rejected_token"` or
`"replay_attempt"` entry is written to the federation audit log. The
caller retains its cursor and retries next cycle.

### FM-6 · Scope boundary violation

Peers can only pull facts for scopes declared in their
`PeerDeclaration`, regardless of token claims. `local`-scope facts
never leave origin (Spec-05-Federation-Trust scope enforcement,
verified: `TestScopeIsolation`). Violations are rejected with HTTP
403 and logged as `event_type="scope_violation"`.

See the [scope propagation guide](./scope-propagation) for
`company`-scoped re-federation restrictions.

## Teardown

```bash
docker compose -f docker-compose.soak.yml down -v
```

The `-v` flag removes data volumes so the next run starts from a
clean state.

## See also

<div className="stigmem-next">

<a href="../../get-started/quickstart-tutorial">
<strong>Get started</strong>
<span>Quickstart</span>
<small>Two-node setup in under 10 minutes.</small>
</a>

<a href="./federation">
<strong>Concepts</strong>
<span>Federation overview</span>
<small>PeerDeclaration, cursor behavior, audit log.</small>
</a>

<a href="./relay-backpressure">
<strong>Concepts</strong>
<span>Relay backpressure</span>
<small>Lag signals in N-node topologies.</small>
</a>

<a href="./scope-propagation">
<strong>Concepts</strong>
<span>Scope propagation</span>
<small>Scope invariants across relay hops.</small>
</a>

</div>
