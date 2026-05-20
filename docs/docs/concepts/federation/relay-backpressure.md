---
title: N-node Relay Backpressure
sidebar_label: Relay Backpressure
audience: Integrator
---

# N-node Relay Backpressure

<p className="stigmem-meta"><span>3 min read</span><span>Node operator · Multi-hop topology</span><span>Spec-05-Federation-Trust</span></p>

<div className="stigmem-lead">

**What this page is**

How relay nodes signal replication lag to downstream peers in
multi-hop federation chains. Lets D distinguish "C is up to date"
from "C is 8 minutes behind A" — even when C is serving D at full
rate.

</div>

:::info Modular spec
N-node backpressure patterns are covered by Spec-05-Federation-Trust
relay-backpressure guidance. These behaviors are **SHOULD**
(recommended), not **MUST** — conformant nodes that omit them will
interoperate but downstream nodes may receive stale data without
warning.
:::

## The problem · silent stale data in relay chains

In a two-node federation (`A ← B`), replication lag is directly
observable: B can see its own pull latency against A.

In an N-node chain (`A ← B ← C ← D`), node C can fall behind B's
replication while continuing to serve D at full rate — meaning **D
receives facts that are stale by both B's lag and C's additional
lag, with no signal that anything is wrong**.

## Backpressure signal · `X-Stigmem-Replication-Lag`

When a node's inbound replication lag exceeds
`STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS` (default 60 seconds), it
includes a warning header on pull responses:

```
X-Stigmem-Replication-Lag: 87450
```

The value is the maximum lag in milliseconds across all inbound
peers. Downstream nodes receiving this header SHOULD:

<div className="stigmem-grid">

<div><h4>Log and alert</h4><p>Log the lag and alert an operator if it persists.</p></div>
<div><h4>Treat synthesized facts as stale</h4><p>Treat synthesized facts from this node as potentially stale.</p></div>
<div><h4>Optionally back off pull interval</h4><p>To reduce load on the lagging node.</p></div>

</div>

## Hard throttle · HTTP 503

When lag exceeds `STIGMEM_FEDERATION_RELAY_LAG_HARD_MS` (default 5
minutes), the node returns HTTP 503 on pull requests:

```json
HTTP/1.1 503 Service Unavailable
Retry-After: 120

{
  "error": "relay_lag_exceeded",
  "lag_ms": 342000,
  "retry_after_s": 120
}
```

<div className="stigmem-keypoint">

**Downstream nodes MUST respect the `retry_after_s` value and not retry before that window.**

</div>

## Discovery via `/.well-known/stigmem`

Nodes expose their current relay lag in the well-known endpoint so
operators can observe it without triggering a pull:

```bash
curl $STIGMEM_URL/.well-known/stigmem | jq .replication_lag_ms
# 87450
```

The `replication_lag_ms` field is:

<div className="stigmem-grid">

<div><h4>Maximum lag</h4><p>Across all inbound peers.</p></div>
<div><h4>Omitted if leaf node</h4><p>No inbound federation, or lag is within warning bounds.</p></div>

</div>

## Environment variables

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS</code></dt>
<dt><span className="stigmem-fields__type"><code>60000</code></span></dt>
<dd>Lag threshold for <code>X-Stigmem-Replication-Lag</code> warning header.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_RELAY_LAG_HARD_MS</code></dt>
<dt><span className="stigmem-fields__type"><code>300000</code></span></dt>
<dd>Lag threshold for HTTP 503 throttle.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_RELAY_ENABLED</code></dt>
<dt><span className="stigmem-fields__type"><code>true</code></span></dt>
<dd>Set <code>false</code> on leaf nodes to disable relay behavior.</dd>
</div>

</div>

Set `STIGMEM_FEDERATION_RELAY_ENABLED=false` on leaf nodes (nodes
with no downstream peers) to suppress relay headers and avoid
unnecessary lag computation.

## Example · 4-node topology

```
A (origin) ← B (relay) ← C (relay) ← D (leaf)
```

<div className="stigmem-fields">

<div>
<dt>Node</dt>
<dt><span className="stigmem-fields__type">Role</span></dt>
<dd>Configuration</dd>
</div>

<div>
<dt>A</dt>
<dt><span className="stigmem-fields__type">origin / source of truth</span></dt>
<dd>No inbound peers; sets <code>RELAY_ENABLED=false</code>.</dd>
</div>

<div>
<dt>B</dt>
<dt><span className="stigmem-fields__type">relay</span></dt>
<dd>Pulls from A; exposes <code>replication_lag_ms</code> in well-known; serves C.</dd>
</div>

<div>
<dt>C</dt>
<dt><span className="stigmem-fields__type">relay</span></dt>
<dd>Pulls from B; propagates lag signal if B falls behind; serves D.</dd>
</div>

<div>
<dt>D</dt>
<dt><span className="stigmem-fields__type">leaf</span></dt>
<dd>Pulls from C; reads <code>X-Stigmem-Replication-Lag</code> on responses from C; <code>RELAY_ENABLED=false</code>.</dd>
</div>

</div>

D's agent should check `X-Stigmem-Replication-Lag` on every pull
response from C and surface it if lag is significant:

```bash
# Check for lag header on pull response
response=$(curl -si $NODE_C_URL/v1/federation/pull \
  -H "Authorization: Bearer $NODE_C_PEER_TOKEN")

lag=$(echo "$response" | grep -i 'x-stigmem-replication-lag' | awk '{print $2}' | tr -d '\r')
if [ -n "$lag" ] && [ "$lag" -gt 30000 ]; then
  echo "Warning: C is ${lag}ms behind A. Facts may be stale."
fi
```

## Operator checklist

<ol className="stigmem-steps">
<li>Set <code>STIGMEM_FEDERATION_RELAY_ENABLED=false</code> on all leaf nodes.</li>
<li>Configure <code>RELAY_LAG_WARNING_MS</code> and <code>RELAY_LAG_HARD_MS</code> for your topology's acceptable freshness window.</li>
<li>Monitor <code>/.well-known/stigmem#replication_lag_ms</code> on relay nodes.</li>
<li>Alert if any relay node exceeds warning threshold for more than 5 minutes.</li>
<li>Downstream agents: check <code>X-Stigmem-Replication-Lag</code> at context-injection time and log when stale.</li>
</ol>

## See also

<div className="stigmem-next">

<a href="./federation">
<strong>Concepts</strong>
<span>Federation overview</span>
<small>Peer registration, pull protocol, and PeerDeclaration setup.</small>
</a>

<a href="./scope-propagation">
<strong>Concepts</strong>
<span>Scope propagation</span>
<small>Scope invariants in N-node topologies.</small>
</a>

<a href="./federation-4node">
<strong>Concepts</strong>
<span>4-node federation</span>
<small>Soak invariants in a relay chain.</small>
</a>

</div>
