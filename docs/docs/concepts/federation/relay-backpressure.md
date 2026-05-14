---
title: N-node Relay Backpressure
sidebar_label: Relay Backpressure
audience: Integrator
---

# N-node Relay Backpressure

:::info Modular spec
N-node backpressure patterns are covered by Spec-05-Federation-Trust relay-backpressure guidance. These behaviors are **SHOULD** (recommended), not **MUST** — conformant nodes that omit them will interoperate but downstream nodes may receive stale data without warning.
:::

**Audience:** Node operators configuring multi-hop federation topologies (three or more nodes in a relay chain).

## The problem: silent stale data in relay chains

In a two-node federation (`A ← B`), replication lag is directly observable: B can see its own pull latency against A. In an N-node chain (`A ← B ← C ← D`), node C can fall behind B's replication while continuing to serve D at full rate — meaning D receives facts that are stale by both B's lag and C's additional lag, with no signal that anything is wrong.

Without backpressure signals, D has no way to distinguish "C is up to date" from "C is 8 minutes behind A."

## Backpressure signal: `X-Stigmem-Replication-Lag`

When a node's inbound replication lag exceeds `STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS` (default 60 seconds), it includes a warning header on pull responses:

```
X-Stigmem-Replication-Lag: 87450
```

The value is the maximum lag in milliseconds across all inbound peers. Downstream nodes receiving this header SHOULD:

- Log the lag and alert an operator if it persists
- Treat synthesized facts from this node as potentially stale
- Optionally back off their own pull interval to reduce load on the lagging node

## Hard throttle: HTTP 503

When lag exceeds `STIGMEM_FEDERATION_RELAY_LAG_HARD_MS` (default 5 minutes), the node returns HTTP 503 on pull requests:

```json
HTTP/1.1 503 Service Unavailable
Retry-After: 120

{
  "error": "relay_lag_exceeded",
  "lag_ms": 342000,
  "retry_after_s": 120
}
```

Downstream nodes MUST respect the `retry_after_s` value and not retry before that window.

## Discovery via `/.well-known/stigmem`

Nodes expose their current relay lag in the well-known endpoint so operators can observe it without triggering a pull:

```bash
curl $STIGMEM_URL/.well-known/stigmem | jq .replication_lag_ms
# 87450
```

The `replication_lag_ms` field is:
- The maximum lag across all inbound peers
- Omitted if the node is a leaf node (no inbound federation) or lag is within warning bounds

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS` | `60000` | Lag threshold for `X-Stigmem-Replication-Lag` warning header |
| `STIGMEM_FEDERATION_RELAY_LAG_HARD_MS` | `300000` | Lag threshold for HTTP 503 throttle |
| `STIGMEM_FEDERATION_RELAY_ENABLED` | `true` | Set `false` on leaf nodes to disable relay behavior |

Set `STIGMEM_FEDERATION_RELAY_ENABLED=false` on leaf nodes (nodes with no downstream peers) to suppress relay headers and avoid unnecessary lag computation.

## Example: 4-node topology

```
A (origin) ← B (relay) ← C (relay) ← D (leaf)
```

In this topology:

- **A** — source of truth; no inbound peers; sets `RELAY_ENABLED=false`
- **B** — pulls from A; exposes `replication_lag_ms` in well-known; serves C
- **C** — pulls from B; propagates lag signal if B falls behind; serves D
- **D** — leaf; pulls from C; reads `X-Stigmem-Replication-Lag` on responses from C; `RELAY_ENABLED=false`

D's agent should check `X-Stigmem-Replication-Lag` on every pull response from C and surface it if lag is significant:

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

For multi-hop topologies:

- [ ] Set `STIGMEM_FEDERATION_RELAY_ENABLED=false` on all leaf nodes
- [ ] Configure `RELAY_LAG_WARNING_MS` and `RELAY_LAG_HARD_MS` for your topology's acceptable freshness window
- [ ] Monitor `/.well-known/stigmem#replication_lag_ms` on relay nodes
- [ ] Alert if any relay node exceeds warning threshold for more than 5 minutes
- [ ] Downstream agents: check `X-Stigmem-Replication-Lag` at context-injection time and log when stale

## See also

- [Federation guide](./)  — peer registration, pull protocol, and PeerDeclaration setup
- [Scope propagation guide](./scope-propagation) — scope invariants in N-node topologies
- Spec-05-Federation-Trust.7 — N-node backpressure patterns
- Spec-05-Federation-Trust — Federation protocol
