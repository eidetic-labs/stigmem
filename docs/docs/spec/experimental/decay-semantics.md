---
spec_id: Spec-X9-Decay-Semantics
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-14
supersedes: pre-reset §15 decay semantics material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-03-HTTP-API >= 0.1.0-alpha.0
title: §15. Decay Semantics
sidebar_label: §15 Decay Semantics
audience: Spec
description: "Stigmem spec section 15 — Configurable TTL and confidence-decay policies; POST /v1/decay/sweep."
stability: experimental
since: 0.9.0a1
---

# §15. Decay Semantics {#section-15}

<p className="stigmem-meta"><span>5 min read</span><span>Spec contributor · Node operator</span><span>Experimental · future plugin line</span></p>

<div className="stigmem-lead">

**What this section covers**

Configurable TTL and confidence-decay policies; `POST /v1/decay/sweep`.
The decay operation is the **remediation complement to lint**: lint
identifies stale/low-confidence facts; the decay sweeper acts on them.

</div>

**Status:** Experimental / dormant source package

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for decay semantics.

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

> **Pre-reset status:** Draft. The decay sweeper (`POST /v1/decay/sweep`) and `decay_scope`
> MCP tool are specified here. Implementation is the D4 deliverable. Wire
> format and DecayPolicy registry are draft; conformance test vectors (`DECAY_VECTORS`)
> will be finalized with D4 implementation.

### §15.1 DecayPolicy {#section-15-1}

A `DecayPolicy` configures how facts of a given relation (or all relations) decay over time. Operators deploy one or more policies to ensure knowledge does not accumulate indefinitely — stale facts degrade confidence or are retracted without requiring agents to remember which facts they once asserted.

<div className="stigmem-keypoint">

**The struct exposes two mutually-exclusive decay modes.**

**Retraction** (`ttl_s`) is an aggressive binary cut-off suited for
ephemeral state. **Confidence reduction** (`half_life_s`) provides
a smoother signal for beliefs that age gradually.

</div>

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

<div className="stigmem-fields">

<div>
<dt>Configuration</dt>
<dt><span className="stigmem-fields__type">Source</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Env var</dt>
<dt><span className="stigmem-fields__type"><code>STIGMEM_DECAY_POLICIES</code></span></dt>
<dd>JSON array of <code>DecayPolicy</code> objects.</dd>
</div>

<div>
<dt>Admin API</dt>
<dt><span className="stigmem-fields__type"><code>/v1/decay/policies</code></span></dt>
<dd>Management endpoint; not yet implemented.</dd>
</div>

<div>
<dt>Default policy</dt>
<dt><span className="stigmem-fields__type">no-op</span></dt>
<dd>If no policies are configured, the decay sweeper is a no-op. Nodes do not apply any automatic decay by default.</dd>
</div>

<div>
<dt>Evaluation order</dt>
<dt><span className="stigmem-fields__type">most-specific-first</span></dt>
<dd>Exact <code>relation</code> match before <code>"&#42;"</code>, exact <code>scope</code> match before <code>"&#42;"</code>. The first matching policy wins.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**The `stigmem:` and `rel:` namespaces are always exempt from decay.**

System-generated facts and reification primitives MUST NOT be
retracted or confidence-reduced by the sweeper, regardless of
policy configuration. The `exempt_relations` field may add further
exemptions.

</div>

### §15.2 Decay Sweep Wire Format {#section-15-2}

The sweep endpoint triggers evaluation of all matching decay policies against a single scope. The request/response split between "actual" and "dry-run" counters is intentional: `facts_retracted` and `facts_reduced` are always zero in `dry_run` mode, while `dry_run_would_retract` and `dry_run_would_reduce` are always zero outside it. This avoids ambiguity about whether writes occurred.

#### Request

```
POST /v1/decay/sweep
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "scope":    FactScope,    // required: which scope to sweep
  "mode":     DecayMode?,   // optional: override all policies' mode for this run
  "policy_id": string?      // optional: run only this named policy
}
```

#### Response

```
200 OK
{
  "swept_at":          string,
  "scope":             FactScope,
  "mode":              DecayMode,
  "facts_evaluated":   integer,
  "facts_retracted":   integer,
  "facts_reduced":     integer,
  "dry_run_would_retract": integer,
  "dry_run_would_reduce":  integer,
  "policies_applied":  string[]
}
```

#### Error responses

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type">validation</span></dt>
<dd><code>scope</code> missing or invalid; <code>policy_id</code> not found; invalid <code>mode</code> override.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type">authorization</span></dt>
<dd>Caller's key lacks write access to the requested scope.</dd>
</div>

<div>
<dt>202</dt>
<dt><span className="stigmem-fields__type">async</span></dt>
<dd>Scope exceeds 100,000 facts (async path; same pattern as §14.5).</dd>
</div>

</div>

The caller's API key MUST have write access to the requested scope. The decay sweep writes retractions (new facts with `confidence=0.0`) or confidence-update facts; these are regular fact assertions subject to all normal write invariants.

### §15.3 Decay and Immutability {#section-15-3}

<div className="stigmem-keypoint">

**The decay sweeper does not mutate existing facts.**

All decay actions are expressed as new immutable fact assertions.
The original fact is retained.

</div>

<div className="stigmem-fields">

<div>
<dt>Action</dt>
<dt><span className="stigmem-fields__type">Output fact</span></dt>
<dd>Source</dd>
</div>

<div>
<dt>Retraction</dt>
<dt><span className="stigmem-fields__type">confidence=0.0</span></dt>
<dd>New fact <code>(entity, relation, scope, confidence=0.0, source="system:stigmem:decay")</code>.</dd>
</div>

<div>
<dt>Confidence reduction</dt>
<dt><span className="stigmem-fields__type">exponential</span></dt>
<dd>New fact with <code>confidence = original_confidence * exp(-ln(2) / half_life_s * elapsed_s)</code>, floored at <code>min_confidence</code>.</dd>
</div>

</div>

Both produce entries in the normal facts table and are visible in `GET /v1/facts` responses. `source="system:stigmem:decay"` allows callers to distinguish sweep-induced retractions from agent-authored retractions.

### §15.4 Performance Contract {#section-15-4}

<div className="stigmem-grid">

<div><h4>Sync within 60 s</h4><p>For scopes with fewer than 100,000 facts.</p></div>
<div><h4>Async over 100k</h4><p>HTTP 202 following the same async job pattern as §14.5.</p></div>
<div><h4>Dry-run always sync</h4><p>Performs no writes and MUST respond within 30 seconds regardless of scope size.</p></div>

</div>

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

<div className="stigmem-keypoint">

**The sweep is idempotent.**

Running it twice in a row on the same data produces the same result.

</div>

Operators define decay policies as a JSON array in the `STIGMEM_DECAY_POLICIES` environment variable. Each entry declares a relation glob, scope, mode, and the relevant timing parameter. Multiple policies can coexist so that different relation families decay at different rates.

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

<div className="stigmem-fields">

<div>
<dt>Vector ID</dt>
<dt><span className="stigmem-fields__type">Mode</span></dt>
<dd>Expected outcome</dd>
</div>

<div>
<dt><code>decay-confidence-reduction</code></dt>
<dt><span className="stigmem-fields__type">confidence</span></dt>
<dd>Fact with <code>half_life_s=3600</code>; asserted 7200 s ago → new fact with <code>confidence ≈ 0.25</code>.</dd>
</div>

<div>
<dt><code>decay-retraction</code></dt>
<dt><span className="stigmem-fields__type">retract</span></dt>
<dd>Fact older than <code>ttl_s</code> → new fact with <code>confidence=0.0</code>, <code>source="system:stigmem:decay"</code>.</dd>
</div>

<div>
<dt><code>decay-scope-filter</code></dt>
<dt><span className="stigmem-fields__type">retract</span></dt>
<dd>Stale fact in <code>public</code> scope; sweep <code>company</code> → no facts retracted (scope isolation).</dd>
</div>

<div>
<dt><code>decay-dry-run</code></dt>
<dt><span className="stigmem-fields__type">dry_run</span></dt>
<dd>Fact older than <code>ttl_s</code> → <code>dry_run_would_retract=1</code>; no new facts in store.</dd>
</div>

<div>
<dt><code>decay-exempt</code></dt>
<dt><span className="stigmem-fields__type">retract</span></dt>
<dd>Fact with <code>relation="stigmem:received_from"</code> → not retracted (exempt namespace).</dd>
</div>

</div>

All five vectors MUST pass for conformance.

---
