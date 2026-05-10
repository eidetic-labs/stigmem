---
title: §14. Lint Semantics
sidebar_label: §14 Lint Semantics
audience: Spec
description: "Stigmem spec section 14 — POST /v1/lint — orphan relations, scope-escalation violations, contradiction surfacing."
---

# §14. Lint Semantics {#section-14}

**Status:** Stable

POST /v1/lint — orphan relations, scope-escalation violations, contradiction surfacing.

**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

The **lint** operation is a first-class Stigmem protocol operation that performs
health-check sweeps over a bounded scope or entity. Lint is strictly **read-only**:
it observes and reports issues without writing facts or modifying node state.

Lint bridges the decay engine (§15) and the current production node.
Running `lint_scope` against a live node reveals knowledge-base health degradation
before it affects query results or agent behavior.

### §14.1 Lint Checks {#section-14-1}

Four normative checks, each independently selectable:

| Check | What it detects |
|---|---|
| `contradiction` | Facts sharing the same `(entity, relation, scope)` tuple where both have `confidence > 0.0` and the conflict is unresolved (status `"unresolved"` in the `conflicts` table). |
| `stale` | Facts whose `valid_until < now` and whose `confidence > 0.0`; optionally, facts whose `valid_until < now + stale_lookahead_s` (approaching expiry). |
| `orphan` | Entities where every known fact is either retracted (`confidence = 0.0`) or expired (`valid_until < now`). No live facts remain for the entity. |
| `broken_ref` | Facts with `value.type = "ref"` whose `value.v` targets an entity or fact ID that has no live (non-retracted, non-expired) facts on this node. |

**Default behavior:** If `checks` is omitted or empty, all four checks run.

**Scope of search:** Each check operates within the `scope` specified in the lint
request. Checks never cross scope boundaries — a `broken_ref` finding in `company` scope
is only reported if the broken ref also falls within `company` scope.

### §14.2 LintFinding Shape {#section-14-2}

```
LintFinding {
  check:    "contradiction" | "stale" | "orphan" | "broken_ref"
  severity: "error" | "warning" | "info"
  entity:   URI               // entity under examination
  relation: string | null     // relevant relation; null for the orphan check
  fact_ids: UUID[]            // IDs of the fact(s) involved in the finding
  detail:   string            // human-readable explanation suitable for display
}
```

### §14.3 Severity Mapping {#section-14-3}

| Check | Condition | Severity |
|---|---|---|
| `contradiction` | Unresolved conflict between two live facts | `error` |
| `stale` | `valid_until < now` and `confidence > 0.0` | `warning` |
| `stale` | `valid_until < now + stale_lookahead_s` (not yet expired but approaching) | `info` |
| `orphan` | Entity has no live facts | `info` |
| `broken_ref` | Ref target entity has no live facts in this node's store | `warning` |
| `broken_ref` | Broken ref where `relation` is `intent:handoff_to` or `intent:context_ref` | `error` |

**Severity rationale:**
- `contradiction` is always `error` — unresolved contradictions corrupt query results for all callers.
- `stale` and `orphan` are non-critical health signals; expired or empty entities do not block reads.
- `broken_ref` on intent-routing relations (`intent:handoff_to`, `intent:context_ref`) is `error`
  because a broken handoff silently discards agent context during delegation.

### §14.4 Wire Format {#section-14-4}

#### Request

```
POST /v1/lint
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "scope":             FactScope,   // required: which scope to sweep
  "checks":            string[],    // optional; default: ["contradiction","stale","orphan","broken_ref"]
  "entity":            URI?,        // optional: restrict sweep to one entity
  "relation":          string?,     // optional: restrict sweep to one relation
  "stale_lookahead_s": integer?     // optional: also flag facts expiring within N seconds; default 0
}
```

#### Response

```
200 OK
{
  "findings":   LintFinding[],   // zero or more findings; empty array = clean
  "checked_at": string,          // ISO 8601 UTC timestamp of when the sweep ran
  "scope":      FactScope,       // echoed from the request
  "checks_run": string[],        // which checks actually ran (echoed or defaulted)
  "fact_count": integer          // number of facts scanned (not findings; helps gauge sweep completeness)
}
```

#### Authorization

The caller's API key must have read access to the requested `scope` (§3.5). Nodes MUST
return HTTP 403 if the key's `allowed_scopes` does not include the requested `scope`.

#### Error responses

| HTTP | Condition |
|---|---|
| 400 | `scope` field missing or invalid; unknown `checks` value |
| 403 | Caller's key is not authorized for the requested scope |
| 202 | Scope exceeds 100,000 facts (async path; see §14.5) |

### §14.5 Performance Contract {#section-14-5}

- `POST /v1/lint` MUST respond synchronously within **30 seconds** for scopes with fewer
  than 100,000 facts.
- For scopes exceeding 100,000 facts, nodes MAY respond with **HTTP 202**:
  ```
  202 Accepted
  { "job_id": "<uuid>", "status": "pending", "estimated_s": integer }
  ```
  The caller polls `GET /v1/lint/jobs/:job_id` until `status` is `"done"` or `"failed"`.
  The async job API is specified here but deferred to the v0.9 substrate window implementation.
- The sweep MUST be **read-only**. Nodes MUST NOT assert, retract, or update any fact
  as a side effect of a lint call. This invariant applies even to internal bookkeeping.

### §14.6 Relationship to Other Operations {#section-14-6}

Lint is **diagnostic**, not prescriptive:

| Finding type | Lint reports | Remediation action (separate call) |
|---|---|---|
| `contradiction` | Which facts conflict | `POST /v1/conflicts/:id/resolve` (§5.10) |
| `stale` | Which facts have expired | `POST /v1/decay/sweep` with `mode="retract"` (§15) or `POST /v1/facts` with `confidence=0.0` |
| `orphan` | Which entities have no live facts | No action required; orphans are informational |
| `broken_ref` | Which ref facts have missing targets | Assert missing target entity, or retract the broken ref |

### §14.7 MCP Tool: `lint_scope` {#section-14-7}

The `lint_scope` MCP tool exposes `POST /v1/lint` to any MCP-aware agent without SDK
installation.

#### Tool definition

```json
{
  "name": "lint_scope",
  "description": "Sweep a Stigmem scope for knowledge-base health issues. Checks for: unresolved contradictions, stale or expiring facts, orphaned entities with no live facts, and broken cross-references. Read-only — reports findings without modifying any facts. Use resolve_contradiction to fix contradictions found here.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "scope": {
        "type": "string",
        "enum": ["local", "team", "company", "public"],
        "description": "The fact scope to sweep."
      },
      "checks": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["contradiction", "stale", "orphan", "broken_ref"]
        },
        "description": "Which checks to run. Omit to run all four."
      },
      "entity": {
        "type": "string",
        "description": "Optional. Restrict sweep to facts about a single entity URI."
      },
      "relation": {
        "type": "string",
        "description": "Optional. Restrict sweep to a single relation."
      },
      "stale_lookahead_s": {
        "type": "integer",
        "description": "Optional. Also flag facts expiring within this many seconds. Default 0 (expired-only)."
      }
    },
    "required": ["scope"]
  }
}
```

#### Output shape

```json
{
  "findings": [
    {
      "check": "contradiction",
      "severity": "error",
      "entity": "stigmem://company.example/user/alice",
      "relation": "memory:role",
      "fact_ids": ["fact-uuid-1", "fact-uuid-2"],
      "detail": "Two live facts with different values for (entity, relation, scope)"
    }
  ],
  "checked_at": "2026-05-02T14:00:00Z",
  "scope": "company",
  "checks_run": ["contradiction", "stale", "orphan", "broken_ref"],
  "fact_count": 1024
}
```

### §14.8 Conformance Test Vectors {#section-14-8}

Normative lint vectors are defined in `sdks/stigmem-py/tests/conformance_vectors.py`
under `LINT_VECTORS`. Each vector includes a `setup` list of fact assertions to run
before the lint sweep, so results are deterministic.

**Required vectors for conformance:**

| Vector ID | Check | Scenario | Expected `findings` |
|---|---|---|---|
| `lint-contradiction` | `contradiction` | Two facts same (entity, relation, scope), different values, both confidence > 0 | ≥1 finding, check=`contradiction`, severity=`error` |
| `lint-stale` | `stale` | Fact with `valid_until` in the past | ≥1 finding, check=`stale`, severity=`warning` |
| `lint-stale-lookahead` | `stale` | Fact with `valid_until` within lookahead window but not yet elapsed | ≥1 finding, check=`stale`, severity=`info` |
| `lint-orphan` | `orphan` | Entity with only retracted facts (confidence=0.0) | ≥1 finding, check=`orphan`, severity=`info` |
| `lint-broken-ref` | `broken_ref` | Ref fact pointing to entity with no live facts | ≥1 finding, check=`broken_ref`, severity=`warning` |
| `lint-broken-ref-intent` | `broken_ref` | Broken ref on `intent:handoff_to` relation | ≥1 finding, check=`broken_ref`, severity=`error` |
| `lint-clean` | all | Scope with only one healthy live fact | findings = `[]` |
| `lint-scope-filter` | `contradiction` | Contradiction exists in `company` scope; lint request on `local` scope | findings = `[]` (scope isolation) |

All eight vectors MUST pass against a reference Stigmem node for conformance.

---
