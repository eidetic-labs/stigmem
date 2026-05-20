---
title: Spec-20 Lint Semantics
sidebar_label: Spec-20 Lint Semantics
audience: Spec
description: "Spec-20-Lint-Semantics rendered entry point — read-only lint checks and finding semantics."
---

# Spec-20-Lint-Semantics \{#section-14\}

<p className="stigmem-meta"><span>5 min read</span><span>Spec contributor · Adapter author</span><span>POST /v1/lint</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-20-Lint-Semantics`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/20-lint-semantics.md).
The **lint** operation is a first-class Stigmem protocol operation
that performs health-check sweeps over a bounded scope or entity.

</div>

<div className="stigmem-keypoint">

**Lint is strictly read-only.**

It observes and reports issues without writing facts or modifying
node state. Lint bridges the decay engine (§15) and the current
production node — running <code>lint_scope</code> against a live
node reveals knowledge-base health degradation before it affects
query results or agent behavior.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the
spec source.
:::

### §14.1 Lint checks \{#section-14-1\}

Four normative checks, each independently selectable.

<div className="stigmem-fields">

<div>
<dt>Check</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>What it detects</dd>
</div>

<div>
<dt><code>contradiction</code></dt>
<dt><span className="stigmem-fields__type">correctness</span></dt>
<dd>Facts sharing the same <code>(entity, relation, scope)</code> tuple where both have <code>confidence &gt; 0.0</code> and the conflict is unresolved (status <code>"unresolved"</code> in the <code>conflicts</code> table).</dd>
</div>

<div>
<dt><code>stale</code></dt>
<dt><span className="stigmem-fields__type">freshness</span></dt>
<dd>Facts whose <code>valid_until &lt; now</code> and <code>confidence &gt; 0.0</code>; optionally, facts whose <code>valid_until &lt; now + stale_lookahead_s</code> (approaching expiry).</dd>
</div>

<div>
<dt><code>orphan</code></dt>
<dt><span className="stigmem-fields__type">coverage</span></dt>
<dd>Entities where every known fact is either retracted (<code>confidence = 0.0</code>) or expired (<code>valid_until &lt; now</code>). No live facts remain for the entity.</dd>
</div>

<div>
<dt><code>broken_ref</code></dt>
<dt><span className="stigmem-fields__type">integrity</span></dt>
<dd>Facts with <code>value.type = "ref"</code> whose <code>value.v</code> targets an entity or fact ID that has no live (non-retracted, non-expired) facts on this node.</dd>
</div>

</div>

**Default behavior:** If `checks` is omitted or empty, all four
checks run.

**Scope of search:** Each check operates within the `scope` specified
in the lint request. Checks never cross scope boundaries — a
`broken_ref` finding in `company` scope is only reported if the
broken ref also falls within `company` scope.

### §14.2 LintFinding shape \{#section-14-2\}

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

### §14.3 Severity mapping \{#section-14-3\}

<div className="stigmem-fields">

<div>
<dt>Check · Condition</dt>
<dt><span className="stigmem-fields__type">Severity</span></dt>
<dd>Rationale</dd>
</div>

<div>
<dt><code>contradiction</code> · unresolved conflict between live facts</dt>
<dt><span className="stigmem-fields__type">error</span></dt>
<dd>Unresolved contradictions corrupt query results for all callers.</dd>
</div>

<div>
<dt><code>stale</code> · <code>valid_until &lt; now</code></dt>
<dt><span className="stigmem-fields__type">warning</span></dt>
<dd>Non-critical health signal.</dd>
</div>

<div>
<dt><code>stale</code> · within <code>stale_lookahead_s</code></dt>
<dt><span className="stigmem-fields__type">info</span></dt>
<dd>Approaching expiry but not yet expired.</dd>
</div>

<div>
<dt><code>orphan</code> · entity has no live facts</dt>
<dt><span className="stigmem-fields__type">info</span></dt>
<dd>Expired or empty entities do not block reads.</dd>
</div>

<div>
<dt><code>broken_ref</code> · target has no live facts</dt>
<dt><span className="stigmem-fields__type">warning</span></dt>
<dd>Standard broken-ref.</dd>
</div>

<div>
<dt><code>broken_ref</code> · on <code>intent:handoff_to</code> or <code>intent:context_ref</code></dt>
<dt><span className="stigmem-fields__type">error</span></dt>
<dd>A broken handoff silently discards agent context during delegation.</dd>
</div>

</div>

### §14.4 Wire format \{#section-14-4\}

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
  "fact_count": integer          // number of facts scanned (not findings)
}
```

#### Authorization

The caller's API key must have read access to the requested `scope`
(§3.5). Nodes MUST return HTTP 403 if the key's `allowed_scopes`
does not include the requested `scope`.

#### Error responses

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd><code>scope</code> field missing or invalid; unknown <code>checks</code> value.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Caller's key is not authorized for the requested scope.</dd>
</div>

<div>
<dt>202</dt>
<dt><span className="stigmem-fields__type">async</span></dt>
<dd>Scope exceeds 100,000 facts (async path; see §14.5).</dd>
</div>

</div>

### §14.5 Performance contract \{#section-14-5\}

<div className="stigmem-grid">

<div><h4>Sync ≤ 30s for &lt;100k facts</h4><p><code>POST /v1/lint</code> MUST respond synchronously within <strong>30 seconds</strong> for scopes with fewer than 100,000 facts.</p></div>
<div><h4>Async for larger scopes</h4><p>For scopes exceeding 100,000 facts, nodes MAY respond with HTTP 202 and a <code>job_id</code>. The caller polls <code>GET /v1/lint/jobs/:job_id</code>. Async job API is specified but deferred to the pre-reset substrate work.</p></div>
<div><h4>Read-only invariant</h4><p>The sweep MUST be read-only. Nodes MUST NOT assert, retract, or update any fact as a side effect of a lint call. This invariant applies even to internal bookkeeping.</p></div>

</div>

```
202 Accepted
{ "job_id": "<uuid>", "status": "pending", "estimated_s": integer }
```

### §14.6 Relationship to other operations \{#section-14-6\}

<div className="stigmem-keypoint">

**Lint is diagnostic, not prescriptive.**

</div>

<div className="stigmem-fields">

<div>
<dt>Finding type</dt>
<dt><span className="stigmem-fields__type">Lint reports</span></dt>
<dd>Remediation action (separate call)</dd>
</div>

<div>
<dt><code>contradiction</code></dt>
<dt><span className="stigmem-fields__type">which facts conflict</span></dt>
<dd><code>POST /v1/conflicts/:id/resolve</code> (§5.10).</dd>
</div>

<div>
<dt><code>stale</code></dt>
<dt><span className="stigmem-fields__type">which facts have expired</span></dt>
<dd><code>POST /v1/decay/sweep</code> with <code>mode="retract"</code> (§15) or <code>POST /v1/facts</code> with <code>confidence=0.0</code>.</dd>
</div>

<div>
<dt><code>orphan</code></dt>
<dt><span className="stigmem-fields__type">which entities have no live facts</span></dt>
<dd>No action required; orphans are informational.</dd>
</div>

<div>
<dt><code>broken_ref</code></dt>
<dt><span className="stigmem-fields__type">which ref facts have missing targets</span></dt>
<dd>Assert missing target entity, or retract the broken ref.</dd>
</div>

</div>

### §14.7 MCP tool: `lint_scope` \{#section-14-7\}

The `lint_scope` MCP tool exposes `POST /v1/lint` to any MCP-aware
agent without SDK installation.

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

### §14.8 Conformance test vectors \{#section-14-8\}

Normative lint vectors are defined in
`sdks/stigmem-py/tests/conformance_vectors.py` under `LINT_VECTORS`.
Each vector includes a `setup` list of fact assertions to run before
the lint sweep, so results are deterministic.

**Required vectors for conformance** — all eight MUST pass against a
reference Stigmem node.

<div className="stigmem-fields">

<div>
<dt>Vector ID</dt>
<dt><span className="stigmem-fields__type">Check</span></dt>
<dd>Scenario · expected <code>findings</code></dd>
</div>

<div>
<dt><code>lint-contradiction</code></dt>
<dt><span className="stigmem-fields__type"><code>contradiction</code></span></dt>
<dd>Two facts same (entity, relation, scope), different values, both confidence &gt; 0 → ≥1 finding, check=<code>contradiction</code>, severity=<code>error</code>.</dd>
</div>

<div>
<dt><code>lint-stale</code></dt>
<dt><span className="stigmem-fields__type"><code>stale</code></span></dt>
<dd>Fact with <code>valid_until</code> in the past → ≥1 finding, check=<code>stale</code>, severity=<code>warning</code>.</dd>
</div>

<div>
<dt><code>lint-stale-lookahead</code></dt>
<dt><span className="stigmem-fields__type"><code>stale</code></span></dt>
<dd>Fact with <code>valid_until</code> within lookahead window but not yet elapsed → ≥1 finding, severity=<code>info</code>.</dd>
</div>

<div>
<dt><code>lint-orphan</code></dt>
<dt><span className="stigmem-fields__type"><code>orphan</code></span></dt>
<dd>Entity with only retracted facts → ≥1 finding, severity=<code>info</code>.</dd>
</div>

<div>
<dt><code>lint-broken-ref</code></dt>
<dt><span className="stigmem-fields__type"><code>broken_ref</code></span></dt>
<dd>Ref fact pointing to entity with no live facts → ≥1 finding, severity=<code>warning</code>.</dd>
</div>

<div>
<dt><code>lint-broken-ref-intent</code></dt>
<dt><span className="stigmem-fields__type"><code>broken_ref</code></span></dt>
<dd>Broken ref on <code>intent:handoff_to</code> relation → ≥1 finding, severity=<code>error</code>.</dd>
</div>

<div>
<dt><code>lint-clean</code></dt>
<dt><span className="stigmem-fields__type">all</span></dt>
<dd>Scope with only one healthy live fact → findings = <code>[]</code>.</dd>
</div>

<div>
<dt><code>lint-scope-filter</code></dt>
<dt><span className="stigmem-fields__type"><code>contradiction</code></span></dt>
<dd>Contradiction in <code>company</code> scope; lint request on <code>local</code> scope → findings = <code>[]</code> (scope isolation).</dd>
</div>

</div>
