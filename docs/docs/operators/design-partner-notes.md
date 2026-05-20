---
title: Design Partner Notes — the pre-reset design-partner window Pilots
sidebar_label: Design Partner Notes
audience: Integrator
---

# Design Partner Notes — the pre-reset design-partner window Pilots

<p className="stigmem-meta"><span>3 min read</span><span>Contributor · Integrator</span><span>Pre-reset retrospective</span></p>

<div className="stigmem-lead">

**What this page covers**

Three design-partner pilots ran during the pre-reset design-partner
window: Zep, Letta, and Cognee. Each pilot produced a working
adapter and surfaced feedback that shaped pre-reset spec protocol
decisions.

</div>

**Audience:** Contributors and integrators evaluating stigmem for production adoption.

## Zep

**Adapter:** [`experimental/zep-adapter/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental/zep-adapter) (deferred per [ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md))

Zep stores agent memory as session-scoped "propositions" extracted from dialogue. The adapter bridges these into stigmem facts and back.

**Key integration pattern:**

<div className="stigmem-grid">

<div><h4><code>assert_to_zep(fact, session_id)</code></h4><p>Encodes a stigmem <code>FactRecord</code> as a structured system message and appends it to a Zep session.</p></div>
<div><h4><code>query_from_zep(scope, session_id)</code></h4><p>Fetches Zep's extracted propositions and converts them to <code>FactRecord</code>-compatible dicts.</p></div>

</div>

**Feedback themes:**

<div className="stigmem-grid">

<div><h4>History flooding</h4><p>Zep's proposition model is single-value-per-entity; stigmem's append-only facts give it more history. Adapters need a reconciliation step.</p></div>
<div><h4>Scope as session boundary</h4><p>Zep users wanted <code>session</code>-scoped facts to stay local. Using <code>scope=local</code> maps naturally — local facts never replicate.</p></div>
<div><h4>Confidence passthrough</h4><p>Zep extracts propositions at varying confidence. <code>synthesize_scope</code> correctly surfaces the lower-confidence alternatives.</p></div>

</div>

## Letta

**Adapter:** [`experimental/letta-adapter/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental/letta-adapter) (deferred per [ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md))

Letta is an agent framework with first-class persistent memory blocks. The adapter federates stigmem facts into Letta's in-context memory and back.

**Key integration pattern:**

<div className="stigmem-grid">

<div><h4>Stigmem as coordinator</h4><p>Shared multi-agent coordination layer; Letta's memory blocks hold the per-agent working copy.</p></div>
<div><h4>Wake: synthesis injection</h4><p>On agent wake, <code>synthesize_scope</code> produces a clean conflict-resolved snapshot that is injected into Letta's memory block.</p></div>
<div><h4>Sleep: round-trip</h4><p>On agent sleep, fact assertions in Letta's memory block are round-tripped back to stigmem.</p></div>

</div>

<div className="stigmem-keypoint">

**The Letta pilot drove the `alt_value` / `alt_confidence` fields in `SynthesisEntry`.**

Callers needed to see the losing value, not just know a contradiction
existed. Decay policies were also useful for memory block hygiene —
Letta agent memory tends to accumulate stale "task status" facts;
the `memory:last_seen` retract policy cleaned these automatically.

</div>

## Cognee

**Adapter:** [`experimental/cognee-adapter/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental/cognee-adapter) (deferred per [ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md))

Cognee builds knowledge graphs from unstructured text. The adapter bridges stigmem's (entity, relation, value) triple model with Cognee's graph representation.

**Feedback themes:**

<div className="stigmem-grid">

<div><h4>Namespace discipline</h4><p>Without normalization against <code>Spec-16-Namespace-Registry</code>, Cognee runs used inconsistent relation URIs for the same semantic concept. The adapter now includes a relation normalization step.</p></div>
<div><h4>Source provenance</h4><p>Cognee users needed to know which document a fact came from. The adapter populates <code>source=cognee:doc:&lt;hash&gt;</code>.</p></div>
<div><h4>Fuzzy entity resolution</h4><p>Cognee often extracts the same entity with slightly different text forms. The fuzzy entity resolver was accelerated by this feedback.</p></div>

</div>

## Cross-pilot patterns

<div className="stigmem-fields">

<div>
<dt>Theme</dt>
<dt><span className="stigmem-fields__type">Spec impact</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><strong>Synthesis at boot</strong></dt>
<dt><span className="stigmem-fields__type">Spec-X10-Synthesis</span></dt>
<dd>Primary query pattern → <code>POST /v1/synthesis</code> and <code>synthesize_scope</code> MCP tool.</dd>
</div>

<div>
<dt><strong>Contradiction visibility</strong></dt>
<dt><span className="stigmem-fields__type">SynthesisEntry</span></dt>
<dd>Callers need the losing value → <code>alt_value</code> / <code>alt_confidence</code>.</dd>
</div>

<div>
<dt><strong>Decay for hygiene</strong></dt>
<dt><span className="stigmem-fields__type">Spec-X9-Decay-Semantics</span></dt>
<dd>Stale facts accumulate without eviction → <code>DecayPolicy</code> and <code>POST /v1/decay/sweep</code>.</dd>
</div>

<div>
<dt><strong>Scope as authorization</strong></dt>
<dt><span className="stigmem-fields__type">Spec-02 + Spec-05</span></dt>
<dd>Local/company scoping needs to be strict; not just a label.</dd>
</div>

<div>
<dt><strong>Namespace discipline</strong></dt>
<dt><span className="stigmem-fields__type">Spec-16-Namespace-Registry</span></dt>
<dd>Inconsistent relation URIs degrade query quality; fuzzy entity resolver.</dd>
</div>

</div>

## Connector guides

For production wiring instructions, see the per-connector guides in the Connectors section (coming soon).
