---
title: §15. Decay Semantics
sidebar_label: §15 Decay Semantics
audience: Spec
description: "Stigmem spec section 15 — Configurable TTL and confidence-decay policies; POST /v1/decay/sweep."
---

# §15. Decay Semantics {#section-15}

**Status:** Stable

Configurable TTL and confidence-decay policies; POST /v1/decay/sweep.

**Authoritative source:** [`spec/stigmem-spec-v1.0.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

> **v0.8 status:** Draft. The decay sweeper (`POST /v1/decay/sweep`) and `decay_scope`
> MCP tool are specified here. Implementation is the D4 deliverable. Wire
> format and DecayPolicy registry are draft; conformance test vectors (`DECAY_VECTORS`)
> will be finalized with D4 implementation. This section will be promoted to normative
> in v0.9 once conformance tests pass against a live node.

The **decay** operation applies operator-configured TTL and confidence-reduction policies
to live facts, producing retractions or confidence updates. Decay is the **remediation
complement to lint**: lint identifies stale/low-confidence facts; the decay sweeper acts
on them.

### §15.1 DecayPolicy {#section-15-1}

A `DecayPolicy` configures how facts of a given relation (or all relations) decay over time. Operators deploy one or more policies to ensure knowledge does not accumulate indefinitely — stale facts degrade confidence or are retracted without requiring agents to remember which facts they once asserted.

The struct exposes two mutually-exclusive decay modes. **Retraction** (`ttl_s`) is an aggressive binary cut-off suited for ephemeral state such as "user is online" — once the TTL expires the fact is no longer credible and a zero-confidence retraction is written. **Confidence reduction** (`half_life_s`) provides a smoother signal for beliefs that age gradually; each sweep halves the original confidence until it hits `min_confidence`. The `relation` and `scope` wildcards (`"*"`) allow broad catch-all policies while the `exempt_relations` escape hatch protects system-generated facts (§3.5) and reification primitives whose removal would corrupt the graph.

```
DecayPolicy {
  id:              string          // unique identifier for this policy
  relation:        string | "*"   // relation this policy applies to; "*" = all relations
  scope:           FactScope | "*" // scope this policy applies to; "*" = all scopes
  mode:            DecayMode
  ttl_s:           integer?        // for mode="retract": retract facts older than ttl_s seconds
  half_life_s:     integer?        // for mode="confidence": halve confidence every half_life_s seconds
  min_confidence:  float?          // for mode="confidence": do not reduce below this floor; default 0.0
  exempt_relations: string[]       // relations that are never decayed by this policy (e.g. stigmem: namespace)
}

DecayMode =
  | "retract"      // assert confidence=0.0 for matching facts older than ttl_s
  | "confidence"   // reduce confidence by half every half_life_s seconds; floor at min_confidence
  | "dry_run"      // same logic as retract/confidence but no writes; returns what would be changed
```

**Policy registry:** Nodes maintain a list of `DecayPolicy` objects configured via:
- Environment variable: `STIGMEM_DECAY_POLICIES` (JSON array of `DecayPolicy` objects).
- Admin API: `GET/POST/DELETE /v1/decay/policies` (management endpoint; not yet implemented; Phase 7).

**Default policy:** If no policies are configured, the decay sweeper is a no-op. Nodes do
not apply any automatic decay by default.

**Policy evaluation order:** Policies are evaluated most-specific-first: exact `relation`
match before `"*"`, exact `scope` match before `"*"`. The first matching policy wins.

**Exempt relations:** The `stigmem:` namespace (system-generated facts) and `rel:`
namespace (reification primitives) are always exempt from decay and MUST NOT be
retracted or confidence-reduced by the sweeper, regardless of policy configuration.
The `exempt_relations` field on individual policies may add further exemptions.

### §15.2 Decay Sweep Wire Format {#section-15-2}

The sweep endpoint triggers evaluation of all matching decay policies against a single scope. Callers specify the target `scope` and may optionally override the decay mode (e.g. forcing `dry_run` for a preview without side effects) or restrict evaluation to a single named policy. The response returns counters that let operators and monitoring systems track how many facts were affected, supporting both automated alerting and manual audit.

The request/response split between "actual" and "dry-run" counters is intentional: `facts_retracted` and `facts_reduced` are always zero in `dry_run` mode, while `dry_run_would_retract` and `dry_run_would_reduce` are always zero outside it. This avoids ambiguity about whether writes occurred.

#### Request

The caller supplies the `scope` to sweep and may optionally force a `mode` override (e.g. `dry_run` to preview the sweep without side effects) or restrict evaluation to a single named `policy_id`. All three fields use the same types defined in §15.1; `scope` is the only required parameter.

```
POST /v1/decay/sweep
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "scope":    FactScope,    // required: which scope to sweep
  "mode":     DecayMode?,   // optional: override all policies' mode for this run (e.g. force "dry_run")
  "policy_id": string?      // optional: run only this named policy
}
```

#### Response

The response reports aggregate counters split by actual vs. dry-run activity. In normal mode `facts_retracted` and `facts_reduced` are populated while the `dry_run_*` fields are zero; in `dry_run` mode the reverse holds. This makes it unambiguous whether the sweep wrote anything — operators can pipe the JSON into monitoring dashboards without parsing the request to determine the mode.

```
200 OK
{
  "swept_at":          string,   // ISO 8601 UTC
  "scope":             FactScope,
  "mode":              DecayMode,
  "facts_evaluated":   integer,
  "facts_retracted":   integer,  // 0 in dry_run mode
  "facts_reduced":     integer,  // confidence-reduced; 0 in dry_run mode
  "dry_run_would_retract": integer,  // populated in dry_run mode; 0 otherwise
  "dry_run_would_reduce":  integer,  // populated in dry_run mode; 0 otherwise
  "policies_applied":  string[]  // policy IDs that matched at least one fact
}
```

#### Error responses

| HTTP | Condition |
|---|---|
| 400 | `scope` missing or invalid; `policy_id` not found; invalid `mode` override |
| 403 | Caller's key lacks write access to the requested scope |
| 202 | Scope exceeds 100,000 facts (async path; same pattern as §14.5) |

#### Authorization

The caller's API key MUST have write access to the requested scope. The decay sweep
writes retractions (new facts with `confidence=0.0`) or confidence-update facts;
these are regular fact assertions subject to all normal write invariants.

### §15.3 Decay and Immutability {#section-15-3}

The decay sweeper does **not** mutate existing facts. All decay actions are expressed
as new immutable fact assertions:

- **Retraction:** A new fact `(entity, relation, scope, confidence=0.0, source="system:stigmem:decay")` is asserted. The original fact is retained.
- **Confidence reduction:** A new fact with `confidence = original_confidence * exp(-ln(2) / half_life_s * elapsed_s)` is asserted, floored at `min_confidence`. The `source` is `"system:stigmem:decay"`.

Both produce entries in the normal facts table and are visible in `GET /v1/facts` responses.
`source="system:stigmem:decay"` allows callers to distinguish sweep-induced retractions from
agent-authored retractions.

### §15.4 Performance Contract {#section-15-4}

- `POST /v1/decay/sweep` MUST respond synchronously within **60 seconds** for scopes
  with fewer than 100,000 facts. (Decay is more expensive than lint because it writes.)
- For scopes exceeding 100,000 facts, nodes MAY respond with HTTP 202 following the
  same async job pattern as §14.5.
- **Dry-run is always synchronous.** `mode="dry_run"` performs no writes and MUST
  respond within 30 seconds regardless of scope size.

### §15.5 MCP Tool: `decay_scope` {#section-15-5}

The `decay_scope` MCP tool exposes `POST /v1/decay/sweep` to any MCP-aware agent.

```json
{
  "name": "decay_scope",
  "description": "Apply configured decay policies to a Stigmem scope. Retracts or reduces confidence of stale/aged facts per operator-defined DecayPolicy. Use mode='dry_run' to preview what would change without writing. Complement to lint_scope — lint identifies decay candidates; decay_scope acts on them.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "scope": {
        "type": "string",
        "enum": ["local", "team", "company", "public"],
        "description": "The fact scope to sweep."
      },
      "mode": {
        "type": "string",
        "enum": ["retract", "confidence", "dry_run"],
        "description": "Optional. Override decay mode for this run. Omit to use configured policy modes."
      },
      "policy_id": {
        "type": "string",
        "description": "Optional. Run only the named decay policy."
      }
    },
    "required": ["scope"]
  }
}
```

### §15.6 Cron-Friendly Operation {#section-15-6}

The decay sweeper is designed for scheduled operation:

```bash
# Run decay sweep on company scope daily at 02:00
0 2 * * * curl -X POST $STIGMEM_URL/v1/decay/sweep \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scope": "company"}'
```

The sweep is **idempotent**: running it twice in a row on the same data produces the
same result (the second run sees the retractions written by the first run and finds
no additional facts to retract at the same TTL threshold).

**Cron configuration pattern:** Operators define decay policies as a JSON array in the `STIGMEM_DECAY_POLICIES` environment variable. Each entry declares a relation glob, scope, mode, and the relevant timing parameter (`half_life_s` for confidence decay, `ttl_s` for hard retraction). The sweep endpoint evaluates every matching policy against facts in the requested scope — multiple policies can coexist so that different relation families decay at different rates.

```
STIGMEM_DECAY_POLICIES=[
  {
    "id": "memory-context-decay",
    "relation": "memory:*",
    "scope": "company",
    "mode": "confidence",
    "half_life_s": 604800,
    "min_confidence": 0.1
  },
  {
    "id": "stale-roadmap-retract",
    "relation": "roadmap:status",
    "scope": "company",
    "mode": "retract",
    "ttl_s": 2592000
  }
]
```

### §15.7 Conformance Test Vectors {#section-15-7}

`DECAY_VECTORS` are defined in `sdks/stigmem-py/tests/conformance_vectors.py`.

| Vector ID | Mode | Scenario | Expected outcome |
|---|---|---|---|
| `decay-confidence-reduction` | `confidence` | Fact with `half_life_s=3600`; assert 7200 s ago | New fact with `confidence ≈ 0.25` |
| `decay-retraction` | `retract` | Fact older than `ttl_s`; assert was 3601 s ago | New fact with `confidence=0.0`, `source="system:stigmem:decay"` |
| `decay-scope-filter` | `retract` | Stale fact in `public` scope; sweep `company` scope | No facts retracted (scope isolation) |
| `decay-dry-run` | `dry_run` | Fact older than `ttl_s` | `dry_run_would_retract=1`; no new facts in store |
| `decay-exempt` | `retract` | Fact with `relation="stigmem:received_from"` in scope | Fact not retracted (exempt namespace) |

All five vectors MUST pass for conformance.

---
