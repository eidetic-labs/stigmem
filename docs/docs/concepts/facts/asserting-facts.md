---
title: Asserting Facts
sidebar_label: Asserting Facts
audience: Integrator
---

# Asserting Facts

**Audience:** Node operators and agent developers using the Stigmem REST API or MCP tools.

## FactValue schema

Every fact carries a typed value. The `value` field must be an object with a `type` discriminator and, for all types except `null`, a `v` field holding the payload:

| `type` | `v` type | Example |
|--------|----------|---------|
| `string` | string | `{"type": "string", "v": "active"}` |
| `text` | string (long-form) | `{"type": "text", "v": "Full markdown body…"}` |
| `number` | number | `{"type": "number", "v": 42}` |
| `boolean` | boolean | `{"type": "boolean", "v": true}` |
| `datetime` | ISO 8601 string | `{"type": "datetime", "v": "2026-05-03T14:00:00Z"}` |
| `ref` | entity URI string | `{"type": "ref", "v": "user:alice"}` |
| `null` | (no `v` key) | `{"type": "null"}` |

## Relation naming convention

Relations must carry a namespace prefix separated by `:`, for example `memory:role` or `acme:goal_state`. Bare relation names (e.g. `role`, `goal_state`) are accepted but emit a server warning and risk collisions across agents and integrations.

Convention: use a short, lowercase namespace that identifies the system or team asserting the fact:

```
<namespace>:<predicate>
# Examples
acme:goal_state
memory:prefers
agent:last_heartbeat
infra:deploy_sha
```

## Asserting a fact

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-key' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "dark mode"},
    "source":     "agent:settings",
    "confidence": 1.0,
    "scope":      "local"
  }' | jq .
```

To **update** a fact, assert a new one for the same `(entity, relation, scope)` triple — Stigmem marks the old fact as superseded (see spec §3).

To **retract** a fact, set `"confidence": 0.0`.

## Heartbeat fact-assertion pattern

Agents that run on a periodic heartbeat should assert a standard set of facts at the start (and end) of each run. This gives any observer a consistent view of agent liveness and intent.

### Mandatory assertions (every heartbeat)

```bash
# 1 — last_heartbeat: timestamp of this run
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "agent:my-agent",
    "relation":   "acme:last_heartbeat",
    "value":      {"type": "datetime", "v": "2026-05-03T14:00:00Z"},
    "source":     "agent:my-agent",
    "confidence": 1.0,
    "scope":      "company"
  }'

# 2 — goal_state: what the agent is currently working on
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "agent:my-agent",
    "relation":   "acme:goal_state",
    "value":      {"type": "string", "v": "PROJ-42: writing documentation"},
    "source":     "agent:my-agent",
    "confidence": 1.0,
    "scope":      "company"
  }'
```

### Conditional assertions

Assert these only when the condition applies:

```bash
# blocked_by — when progress is blocked
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "agent:my-agent",
    "relation":   "acme:blocked_by",
    "value":      {"type": "ref", "v": "issue:PROJ-99"},
    "source":     "agent:my-agent",
    "confidence": 1.0,
    "scope":      "company"
  }'

# decision — a decision made this heartbeat (use type: "text" for longer rationale)
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "agent:my-agent",
    "relation":   "acme:decision",
    "value":      {"type": "string", "v": "Deferred API guide to child issue PROJ-55"},
    "source":     "agent:my-agent",
    "confidence": 1.0,
    "scope":      "company",
    "valid_until": "2026-05-03T23:59:59Z"
  }'

# completed — task finished this heartbeat
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "issue:PROJ-42",
    "relation":   "acme:completed",
    "value":      {"type": "boolean", "v": true},
    "source":     "agent:my-agent",
    "confidence": 1.0,
    "scope":      "company"
  }'
```

:::tip Using the MCP tool instead of curl
If you are inside a Paperclip or Claude Code session with the Stigmem MCP server configured, call `assert_fact` directly — no `curl` required. See the [Paperclip connector guide](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/adapter-paperclip).
:::

## Multi-tenant fact assertion

When a node serves multiple tenants, the `tenant_id` is derived automatically from the API key — no extra field in the request body is needed. All facts written with a key scoped to `"acme"` are invisible to keys scoped to any other tenant.

### Asserting a fact as a specific tenant

```bash
# Uses an API key minted with tenant_id="acme"
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACME_KEY" \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "dark mode"},
    "source":     "agent:settings",
    "confidence": 1.0,
    "scope":      "local"
  }' | jq .
```

A key scoped to `"beta"` cannot read or overwrite this fact — `GET /v1/facts?entity=user:alice` returns an empty result for any other tenant.

### Querying facts — tenant-isolated

```bash
# Returns only facts belonging to the "acme" tenant
curl -s "http://localhost:8765/v1/facts?entity=user:alice" \
  -H "Authorization: Bearer $ACME_KEY" | jq .
```

See [Multi-Tenant Scoping](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/multi-tenant) for the full isolation model and key provisioning guide.

## Additional topics

- Retracting a fact: set `"confidence": 0.0` with the same `(entity, relation, scope)` triple
- Reification for N-ary relationships: use `stigmem:rel:<uuid>` as an intermediate entity (see spec §2.3)
- `valid_until`: ISO 8601 expiry; omit for a permanent fact
- Updating facts: see spec §3 for supersession semantics

See the [API Reference](/docs/reference/api) for the full `POST /v1/facts` endpoint spec.
