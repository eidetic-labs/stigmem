---
spec_id: Spec-X10-Synthesis
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-14
supersedes: pre-reset §16 synthesis material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-07-Recall-Pipeline >= 0.1.0-alpha.0
title: §16. Synthesis
sidebar_label: §16 Synthesis
audience: Spec
description: "Stigmem spec section 16 — POST /v1/synthesis — confidence-weighted current-state snapshots per entity/scope."
stability: experimental
since: 0.9.0a1
---

# §16. Synthesis {#section-16}

<p className="stigmem-meta"><span>5 min read</span><span>Spec contributor · SDK author</span><span>Experimental · future plugin line</span></p>

<div className="stigmem-lead">

**What this section covers**

`POST /v1/synthesis` — a confidence-weighted summary view of the
live facts in a scope. Where lint reports raw health findings and
decay sweeps apply remediation, synthesis answers: *"given everything
I know right now, what is the current state of this scope?"*

</div>

**Status:** Experimental / dormant source package

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for synthesis semantics.

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

> **Pre-reset status:** Draft. The `synthesize_scope` MCP tool and `POST /v1/synthesis` route
> are specified here. Implementation is the D4 deliverable. Conformance test
> vectors (`SYNTHESIS_VECTORS`) will be finalized with D4 implementation. This section
> will be promoted to normative in the pre-reset spec.

<div className="stigmem-keypoint">

**Synthesis is designed for agent context injection.**

An agent querying `synthesize_scope("company")` gets a structured
view of the most reliable current knowledge without needing to
manually filter contradictions, expired facts, or low-confidence noise.

</div>

### §16.1 SynthesisEntry Shape {#section-16-1}

Each row in the synthesis response is a `SynthesisEntry` — the collapsed, current-state view of a single `(entity, relation, scope)` triple. Where a raw fact query might return ten historical assertions for "Alice's role," synthesis returns one entry with the highest-confidence live value. If that triple is contradicted (two live values competing), synthesis surfaces both via the `alt_value`/`alt_confidence` fields and flags `contradicted: true` so the consuming agent can decide whether to act on or escalate the ambiguity.

```
SynthesisEntry {
  entity:        URI
  relation:      string
  scope:         FactScope
  value:         FactValue
  confidence:    float          // confidence of the winning fact
  hlc:           string         // HLC of the winning fact
  contradicted:  boolean        // true if unresolved contradiction exists for this (entity, relation, scope)
  alt_value:     FactValue?     // populated if contradicted=true: the other live value
  alt_confidence: float?        // populated if contradicted=true
}
```

### §16.2 Synthesis Algorithm {#section-16-2}

For each `(entity, relation, scope)` triple with at least one live fact (confidence > 0.0, not expired):

<ol className="stigmem-steps">
<li>Apply contradiction resolution order (§3.3): higher confidence wins; equal confidence → higher HLC wins.</li>
<li>If an unresolved contradiction exists, set <code>contradicted=true</code> and populate <code>alt_value</code>/<code>alt_confidence</code> with the losing fact's value and confidence.</li>
<li>Filter by <code>min_confidence</code> (if provided): skip entries where the winning fact's confidence is below the threshold.</li>
<li>Include the entry in the response.</li>
</ol>

Expired facts (`valid_until < now`) and retracted facts (`confidence=0.0`) are excluded unless `include_expired=true` is passed.

### §16.3 Wire Format {#section-16-3}

The synthesis endpoint follows the same request/response conventions as decay (§15.2) and lint (§14). Because synthesis is a read-only aggregation, it never writes facts — the response is a snapshot that may change on the next call if facts are asserted, decayed, or retracted in the interim.

#### Request

The caller specifies the `scope` to synthesize and may narrow results to a single `entity` URI. The `min_confidence` filter is applied after synthesis: entries whose winning confidence falls below the threshold are excluded from the response, which is useful for agents that only want high-certainty knowledge.

```
POST /v1/synthesis
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "scope":           FactScope,   // required
  "entity":          URI?,        // optional: restrict to one entity
  "min_confidence":  float?,      // optional: exclude entries below this confidence; default 0.0
  "include_expired": boolean?     // optional: include expired facts in synthesis; default false
}
```

#### Response

The `summary` array contains one `SynthesisEntry` (§16.1) per live `(entity, relation, scope)` triple. The `contradiction_count` gives a quick signal for whether the scope has unresolved ambiguity — a non-zero value means at least one triple has competing live values. `filtered_count` reports how many entries were excluded by the `min_confidence` threshold, so callers can tell whether lowering the threshold would surface more data.

```
200 OK
{
  "summary":            SynthesisEntry[],
  "synthesized_at":     string,    // ISO 8601 UTC
  "scope":              FactScope,
  "fact_count":         integer,   // total live facts evaluated
  "contradiction_count": integer,  // number of entries with contradicted=true
  "filtered_count":     integer    // entries excluded by min_confidence filter
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
<dd><code>scope</code> missing or invalid; <code>min_confidence</code> out of [0.0, 1.0] range.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type">authorization</span></dt>
<dd>Caller's key lacks read access to the requested scope.</dd>
</div>

</div>

### §16.4 MCP Tool: `synthesize_scope` {#section-16-4}

```json
{
  "name": "synthesize_scope",
  "description": "Produce a confidence-weighted summary of current knowledge in a Stigmem scope. Returns the best current value for each (entity, relation) pair, with contradiction flags where multiple live values exist. Ideal for agent context injection — surfaces reliable current state without requiring manual contradiction filtering.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "scope": {
        "type": "string",
        "enum": ["local", "team", "company", "public"],
        "description": "The fact scope to synthesize."
      },
      "entity": {
        "type": "string",
        "description": "Optional. Restrict synthesis to facts about a single entity URI."
      },
      "min_confidence": {
        "type": "number",
        "description": "Optional. Exclude entries with confidence below this threshold. Range [0.0, 1.0]. Default 0.0."
      }
    },
    "required": ["scope"]
  }
}
```

### §16.5 Relationship to Lint and Decay {#section-16-5}

The three pre-reset design-partner window operational tools form a pipeline:

<div className="stigmem-fields">

<div>
<dt>Tool</dt>
<dt><span className="stigmem-fields__type">Writes?</span></dt>
<dd>Question answered</dd>
</div>

<div>
<dt><code>lint_scope</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>"What is wrong?"</dd>
</div>

<div>
<dt><code>decay_scope</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>"Apply configured remediation" (retractions / confidence updates).</dd>
</div>

<div>
<dt><code>synthesize_scope</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>"What do I currently know?"</dd>
</div>

</div>

The typical agent workflow:

<ol className="stigmem-steps">
<li>Boot: call <code>synthesize_scope</code> to get current reliable knowledge for context injection.</li>
<li>Background (periodic): call <code>lint_scope</code> to identify health issues; optionally call <code>decay_scope</code> to apply configured policies.</li>
<li>Resolution: call <code>POST /v1/conflicts/:id/resolve</code> for contradictions surfaced by lint.</li>
</ol>

---

*the pre-reset spec-draft — §§1–14 promoted (pre-reset). §15 Decay Semantics and §16 Synthesis are draft, pending D4 implementation. §6.7–§6.8 N-node patterns are draft, pending D1 correctness test validation. Open for CTO review before promotion to stable.*
