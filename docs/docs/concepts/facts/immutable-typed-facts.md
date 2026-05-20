---
title: Why Immutable Typed Facts
sidebar_label: Immutable Typed Facts
sidebar_position: 1
description: Why Stigmem stores knowledge as immutable, typed atomic facts — and why mutable key-value stores fail at federation.
---

# Why Immutable Typed Facts

<p className="stigmem-meta"><span>4 min read</span><span>Protocol implementer · SDK author</span><span>Spec-01-Fact-Model</span></p>

<div className="stigmem-lead">

**What this page is**

Why Stigmem stores knowledge as immutable, typed atomic facts —
`(entity, relation, value, source, timestamp, hlc, confidence, scope)`
— and why mutable key-value stores fail at federation.

</div>

## The problem

An AI agent needs to remember things — a user's role, a project's
status, a preference. The simplest model is a key-value store:
`set("alice.role", "CEO")`. But the moment a second agent, a second
node, or a second point in time enters the picture, key-value breaks
down.

<div className="stigmem-keypoint">

**Which write wins? Who wrote it? When? Can you prove the value wasn't tampered with?**

Key-value stores answer none of these questions without bolting on
layers of metadata — at which point you've reinvented a fact model,
just poorly.

</div>

## Naive approaches and why they fail

<div className="stigmem-fields">

<div>
<dt>Approach</dt>
<dt><span className="stigmem-fields__type">Failure mode</span></dt>
<dd>Why it doesn't work</dd>
</div>

<div>
<dt>Mutable key-value store</dt>
<dt><span className="stigmem-fields__type">silent loss</span></dt>
<dd>Two agents write different values for the same key. Last-write-wins silently discards one. No record of the conflict, no provenance, no way to know the discarded value ever existed.</dd>
</div>

<div>
<dt>Append-only log</dt>
<dt><span className="stigmem-fields__type">no structure</span></dt>
<dd>You keep history, but a flat log has no structure. Querying "what does Alice prefer?" requires scanning the entire log. No way to express typed values, confidence levels, or scope boundaries without ad-hoc conventions.</dd>
</div>

<div>
<dt>Document store with versioning</dt>
<dt><span className="stigmem-fields__type">document-level granularity</span></dt>
<dd>Git-style versioning preserves history but treats the document as the unit of change. A single-field update creates a full document revision. Merging divergent revisions requires a schema-aware merge algorithm; schema changes break the merger.</dd>
</div>

</div>

## Our model

Stigmem stores knowledge as **atomic facts**. Each fact is a single
assertion:

```
(entity, relation, value, source, timestamp, hlc, confidence, scope)
```

A fact is immutable once written. Updates are new facts. Retractions
are facts with `confidence = 0.0`. This gives you:

<div className="stigmem-fields">

<div>
<dt>Property</dt>
<dt><span className="stigmem-fields__type">How</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><strong>Audit trail</strong></dt>
<dt><span className="stigmem-fields__type">append-only</span></dt>
<dd>Every assertion ever made is preserved. Nothing is overwritten or deleted.</dd>
</div>

<div>
<dt><strong>Typed values</strong></dt>
<dt><span className="stigmem-fields__type">seven types</span></dt>
<dd><code>string</code>, <code>text</code>, <code>number</code>, <code>boolean</code>, <code>datetime</code>, <code>ref</code>, <code>null</code> (Spec-01-Fact-Model typed values).</dd>
</div>

<div>
<dt><strong>Provenance</strong></dt>
<dt><span className="stigmem-fields__type"><code>source</code> + <code>timestamp</code></span></dt>
<dd>Every fact carries who asserted it and when.</dd>
</div>

<div>
<dt><strong>Confidence</strong></dt>
<dt><span className="stigmem-fields__type">float [0.0, 1.0]</span></dt>
<dd><code>1.0</code> = certain, <code>0.5</code> = uncertain, <code>0.0</code> = retracted.</dd>
</div>

<div>
<dt><strong>Scope</strong></dt>
<dt><span className="stigmem-fields__type">visibility boundary</span></dt>
<dd><code>local</code>, <code>team</code>, <code>company</code>, or <code>public</code> — governs visibility and federation.</dd>
</div>

<div>
<dt><strong>Causal ordering</strong></dt>
<dt><span className="stigmem-fields__type">HLC</span></dt>
<dd>Every fact gets a causally consistent position in time (Spec-12-HLC-Bounded-Skew).</dd>
</div>

</div>

### Worked example · asserting and retracting a fact

```bash
# Assert: Alice is CEO
curl -X POST $STIGMEM_URL/v1/facts \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -d '{
    "entity": "stigmem://company.example/user/alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "stigmem://company.example/agent/assistant",
    "confidence": 1.0,
    "scope": "company"
  }'
# → 201 { "id": "fact_01J...", "hlc": "1746230400000.001", ... }

# Retract: Alice is no longer CEO
curl -X POST $STIGMEM_URL/v1/facts \
  -d '{
    "entity": "stigmem://company.example/user/alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "stigmem://company.example/agent/assistant",
    "confidence": 0.0,
    "scope": "company"
  }'
# → 201 { "id": "fact_02J...", "confidence": 0.0, ... }
```

Both facts exist in the store. The original assertion is never
deleted. Querying `memory:role` for Alice now returns the retraction
(confidence 0.0), and any query with `min_confidence > 0` filters it
out naturally.

### Entity URI structure

Entities use a formal URI scheme that binds identity to the owning
node:

```
stigmem://{authority}/{type}/{id}
```

For example: `stigmem://company.example/user/alice`,
`stigmem://company.example/agent/cto`. This prevents identity
collisions across federated nodes — two peers can each have a
`user/alice` without ambiguity. Entity URIs are normalized to
lowercase on ingest (Spec-01-Fact-Model entity normalization) to
prevent silent fragmentation.

## Why this is non-obvious

<div className="stigmem-grid">

<div><h4>Immutability seems wasteful</h4><p>Storing every version sounds expensive. But mutable state with conflict resolution or distributed locking is <em>more</em> expensive in a federated system. Immutability eliminates an entire class of distributed systems problems: you never need distributed locks, two-phase commits, or merge algorithms. Contradiction detection becomes a simple comparison.</p></div>
<div><h4>Retracting via <code>confidence = 0.0</code> seems indirect</h4><p>But it preserves the retraction as a first-class event with its own provenance. You can answer "who retracted this, and when?" — which matters for compliance (GDPR Art. 17) and debugging. A <code>DELETE</code> operation would destroy that information.</p></div>
<div><h4>Seven value types seem arbitrary</h4><p>They're the minimum set that covers practical agent-memory needs without requiring schema registration. <code>string</code> for labels, <code>text</code> for narrative, <code>number</code>/<code>boolean</code>/<code>datetime</code> for structured data, <code>ref</code> for entity-to-entity links (powers the graph index), <code>null</code> for explicit "unknown."</p></div>

</div>

## What it costs

<div className="stigmem-grid">

<div><h4>Storage</h4><p>Every update creates a new row. For high-churn relations, the facts table grows proportionally. The decay sweeper (Spec-X9) mitigates this by automatically retracting stale facts based on configurable TTL and half-life policies.</p></div>
<div><h4>Query complexity</h4><p>Finding the "current" value for an entity-relation pair requires ordering by HLC and filtering by confidence — not a simple key lookup. The node handles this internally, but implementers should index on <code>(entity, relation, scope)</code>.</p></div>
<div><h4>No partial updates</h4><p>You can't change one field of a fact. You assert a complete new fact. For the atomic assertions Stigmem models, this is acceptable; for document-shaped data, use <code>ref</code>-type values to point to external storage.</p></div>

</div>

## References

<div className="stigmem-next">

<a href="https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md">
<strong>Spec-01-Fact-Model</strong>
<span>Atomic fact shape</span>
<small>Including FactValue types, HLC, entity URI scheme, normalization.</small>
</a>

<a href="./asserting-facts">
<strong>Concepts</strong>
<span>Asserting facts</span>
<small>Wire format for <code>POST /v1/facts</code> and retraction.</small>
</a>

<a href="./conflict-semantics">
<strong>Concepts</strong>
<span>Conflict semantics</span>
<small>How immutability and contradiction detection work together.</small>
</a>

</div>
