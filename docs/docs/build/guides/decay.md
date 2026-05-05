---
id: decay
title: Decay Semantics
sidebar_label: Decay Semantics
audience: Integrator
---

# Decay Semantics

:::caution Experimental
`POST /v1/decay/sweep` and `DecayPolicy` are **draft** in spec v0.8 (§15). The API shape is stable for testing but will be promoted to normative in v0.9. Operator config via environment variable only; admin API is forthcoming.
:::

**Audience:** Node operators and agent developers who need to manage fact freshness — retracting stale data or reducing confidence of aged assertions over time.

## Overview

Stigmem facts are immutable — once asserted, they are never deleted. Decay is how you signal that old facts are no longer reliable:

- **Retract mode** — emits a new zero-confidence fact (same semantics as a manual retraction); excludes the fact from queries by default.
- **Confidence-reduction mode** — emits a new fact with confidence halved every `half_life_s` seconds, down to a configurable floor.
- **Dry-run mode** — previews what would change without writing any facts.

Decay is implemented as immutable fact assertions sourced from `system:stigmem:decay`, not as mutations of existing rows. This preserves the full audit trail (§15.3).

## Quick example

```bash
# Preview what decay would touch in the "company" scope
curl -X POST $STIGMEM_URL/v1/decay/sweep \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scope": "company", "mode": "dry_run"}'
```

```json
{
  "swept_at": "2026-05-02T18:00:00Z",
  "scope": "company",
  "mode": "dry_run",
  "facts_evaluated": 12480,
  "facts_retracted": 0,
  "facts_reduced": 0,
  "dry_run_would_retract": 34,
  "dry_run_would_reduce": 220,
  "policies_applied": ["stale-memory-ttl", "low-confidence-decay"]
}
```

Always run `dry_run` first against production scopes to understand the blast radius before committing.

## Configuring decay policies

Policies are configured via the `STIGMEM_DECAY_POLICIES` environment variable as a JSON array:

```bash
export STIGMEM_DECAY_POLICIES='[
  {
    "id": "stale-memory-ttl",
    "relation": "memory:last_seen",
    "scope": "company",
    "mode": "retract",
    "ttl_s": 2592000
  },
  {
    "id": "low-confidence-decay",
    "relation": "*",
    "scope": "*",
    "mode": "confidence",
    "half_life_s": 604800,
    "min_confidence": 0.1,
    "exempt_relations": ["user:id", "agent:keypair"]
  }
]'
```

**Policy evaluation order:** Most specific first — exact `relation` before `"*"`, exact `scope` before `"*"`. When multiple policies match, the first match wins.

**Always-exempt:** `stigmem:` and `rel:` namespace facts are never decayed regardless of policy.

### `DecayPolicy` schema (§15.1)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier for this policy |
| `relation` | string or `"*"` | yes | Relation to apply decay to; `"*"` matches all |
| `scope` | FactScope or `"*"` | yes | Scope to apply decay to; `"*"` matches all |
| `mode` | `retract` \| `confidence` \| `dry_run` | yes | Decay mode |
| `ttl_s` | integer | retract only | Retract facts older than this many seconds |
| `half_life_s` | integer | confidence only | Halve confidence every this many seconds |
| `min_confidence` | float | confidence only | Floor; confidence never reduced below this (default `0.0`) |
| `exempt_relations` | string[] | no | Relations excluded from this policy |

## Running a decay sweep

```
POST /v1/decay/sweep
Authorization: Bearer <api-key>
Content-Type: application/json
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `scope` | FactScope | yes | Scope to sweep (`local`, `team`, `company`, `public`) |
| `mode` | DecayMode | no | Override all policies' mode for this run |
| `policy_id` | string | no | Run only the named policy |

**Response (200 OK):**

| Field | Description |
|---|---|
| `swept_at` | ISO 8601 UTC timestamp |
| `facts_evaluated` | Total live facts examined |
| `facts_retracted` | Facts retracted (0 in dry_run) |
| `facts_reduced` | Facts with confidence reduced (0 in dry_run) |
| `dry_run_would_retract` | Populated in dry_run mode only |
| `dry_run_would_reduce` | Populated in dry_run mode only |
| `policies_applied` | Policy IDs that matched at least one fact |

**Performance contract (§15.4):**
- Synchronous response within **60 seconds** for scopes under 100k facts
- HTTP 202 (async job) for scopes over 100k facts (same pattern as §14.5)
- Dry-run always synchronous within **30 seconds** regardless of scope size

**Authorization:** caller's API key must have **write access** to the requested scope.

### Error responses

| HTTP | Condition |
|---|---|
| 400 | Missing/invalid `scope`; `policy_id` not found; invalid `mode` override |
| 403 | API key lacks write access to the scope |
| 202 | Scope exceeds 100,000 facts (async path) |

## MCP tool: `decay_scope`

If you are using the stigmem MCP server, the `decay_scope` tool wraps the REST endpoint:

```python
# Via MCP tool call
result = await mcp.call_tool("decay_scope", {
    "scope": "company",
    "mode": "dry_run"
})
```

Use `mode="dry_run"` to preview, then omit `mode` to apply configured policies.

Complement: run `lint_scope` first to see _what_ is wrong, then `decay_scope` to act on it (§15.5).

## Scheduling sweeps

Run decay as a cron job against each scope your node manages:

```bash
# Daily sweep at 02:00 UTC
0 2 * * * curl -s -X POST $STIGMEM_URL/v1/decay/sweep \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scope": "company"}' | jq '{swept_at, facts_retracted, facts_reduced}'
```

## How decay interacts with queries

Decayed facts follow the same visibility rules as manual retractions:

- **Retracted facts** (`confidence=0.0`) are excluded from `GET /v1/facts` responses unless `?include_retracted=true`
- **Confidence-reduced facts** remain visible with their updated confidence value
- Decay-sourced facts carry `source="system:stigmem:decay"` — filter on this field to distinguish system retractions from agent-authored ones

To get a clean current-state view after running decay, use [`synthesize_scope`](/docs/build/guides/synthesis) — it automatically excludes retracted facts and picks the highest-confidence value for each `(entity, relation)` pair.

## See also

- [Synthesis guide](/docs/build/guides/synthesis) — confidence-weighted summary of live facts
- [Conflict resolution guide](/docs/build/guides/conflict-resolution) — resolving contradictions before decay
- Spec §15 — Decay Semantics (authoritative wire format and invariants)
- Spec §3 — Fact immutability and retraction semantics
