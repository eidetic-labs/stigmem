# ADR-006: Batch-assert API for transactional multi-fact writes

<p className="stigmem-meta"><span>5 min read</span><span>Accepted</span><span>Recorded 2026-05-06</span></p>

<div className="stigmem-lead">

**What this ADR decides**

Add `POST /v1/facts:batch` with all-or-nothing semantics. Either every
fact in the batch commits as a single transaction or none do.
Per-fact validation occurs before any write, idempotency is supported
via `Idempotency-Key`, and federation replication treats batches as
units.

</div>

<div className="stigmem-keypoint">

**Status: Accepted.**

Closes the OpenClaw H2 audit finding structurally. Compensating
retractions are a workaround; server-side atomicity is the fix.

</div>

**Date:** 2026-05-06 · **Authors:** Eidetic Labs · **Related:** `stigmem/openclaw/audit.md` H2; OpenClaw adapter v0.9; [ADR-002](./002-v1-scope)

## Context

Several adapter operations write multiple facts as a logical unit: a
handoff (handoff_to + handoff_summary + context_refs + continuation),
an escalation (escalation + escalate_to + goal), a decision with
provenance pointers. These operations are semantically transactional
— a partial write produces an inconsistent state that downstream
readers cannot detect.

The current API exposes only `POST /v1/facts` for single-fact
assertion. Adapters that need to write a multi-fact unit do so by
calling the endpoint repeatedly. If any individual write fails, the
result is partial state: some facts of the logical unit are written,
others are not. The receiving agent boots and sees the partial state
with no signal of incompleteness.

<div className="stigmem-keypoint">

**Compensation is a workaround, not a solution.**

The OpenClaw audit (finding H2) documented this gap in concrete code.
The v0.9 adapter attempts compensating retractions when partial
writes are detected, but compensating retractions can themselves
fail, leaving torn state. The right solution is server-side: a batch
endpoint with all-or-nothing semantics.

</div>

This belongs at the API layer, not the adapter layer, because:

<div className="stigmem-grid">

<div><h4>Every adapter has the same problem</h4></div>
<div><h4>SQLite already supports transactions</h4></div>
<div><h4>Without it, the wire format makes consistent multi-fact writes impossible across the network</h4></div>

</div>

## Decision

We add `POST /v1/facts:batch` with all-or-nothing semantics.

### Endpoint specification

**Request:**

```http
POST /v1/facts:batch
Content-Type: application/json
Authorization: Bearer <api_key>
Idempotency-Key: <optional>

{
 "facts": [
 {
 "entity": "...",
 "relation": "...",
 "value": {...},
 "source": "...",
 "scope": "...",
 "confidence": 1.0,
 "valid_until": null,
 "interpret_as": "content",
 "attestation": null
 },
 ...
 ],
 "atomic": true
}
```

**Response (success):**

```http
HTTP/1.1 200 OK

{
 "facts": [
 {"id": "fact:abc...", "cid": "sha256:..."},
 ...
 ]
}
```

**Response (failure):**

```http
HTTP/1.1 422 Unprocessable Entity

{
 "error": "batch_failed",
 "failed_at_index": 2,
 "reason": "scope_violation: token does not grant write to scope=team",
 "facts_written": 0
}
```

### Semantics

<div className="stigmem-fields">

<div>
<dt>Rule</dt>
<dt><span className="stigmem-fields__type">Behavior</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>1 · All or nothing</dt>
<dt><span className="stigmem-fields__type">atomic</span></dt>
<dd>Either every fact is written and committed, or none are. <code>facts_written</code> confirms which case occurred.</dd>
</div>

<div>
<dt>2 · Validation before any write</dt>
<dt><span className="stigmem-fields__type">pre-commit</span></dt>
<dd>Server validates the entire batch (scope, capability tokens, schema, <code>interpret_as</code>) before committing any. Validation failure on fact N rejects the whole batch with <code>failed_at_index: N</code>.</dd>
</div>

<div>
<dt>3 · Single transaction at the storage layer</dt>
<dt><span className="stigmem-fields__type">SQLite</span></dt>
<dd><code>BEGIN IMMEDIATE</code> for the duration of the batch; rollback on any error. PostgreSQL (v2.0) uses the equivalent.</dd>
</div>

<div>
<dt>4 · Idempotency supported</dt>
<dt><span className="stigmem-fields__type">TTL'd cache</span></dt>
<dd>Client-supplied <code>Idempotency-Key</code> header. Default 24-hour TTL. Already-processed keys return the original response without re-applying.</dd>
</div>

<div>
<dt>5 · Bounded batch size</dt>
<dt><span className="stigmem-fields__type">default 50</span></dt>
<dd><code>STIGMEM_BATCH_MAX_FACTS = 50</code>. Operators can tune; larger batches trade latency for transaction-lock duration.</dd>
</div>

<div>
<dt>6 · Quotas apply per fact</dt>
<dt><span className="stigmem-fields__type">per fact</span></dt>
<dd>A 10-fact batch consumes 10 units of the <code>fact_write</code> quota. Prevents batch as a quota-bypass surface.</dd>
</div>

<div>
<dt>7 · Audit events fire per fact + one batch event</dt>
<dt><span className="stigmem-fields__type">N+1 events</span></dt>
<dd>Each fact emits its <code>fact_write</code> with the same <code>batch_id</code>; an additional <code>batch_assert</code> event records the overall outcome.</dd>
</div>

<div>
<dt>8 · Federation replication treats batches as units</dt>
<dt><span className="stigmem-fields__type">end-to-end</span></dt>
<dd>A batch arriving via federation is replicated as a single unit downstream.</dd>
</div>

</div>

### Adapter migration

Adapters update to use the batch endpoint where they currently issue
multi-fact writes.

<div className="stigmem-grid">

<div>
<h4>OpenClaw <code>emit_handoff</code></h4>
<p>Batch-asserts handoff_to · handoff_summary · context_refs · continuation as one unit.</p>
</div>

<div>
<h4>OpenClaw <code>emit_escalation</code></h4>
<p>Batch-asserts escalation · escalate_to · goal as one unit.</p>
</div>

<div>
<h4>Future adapter operations</h4>
<p>Follow the same pattern.</p>
</div>

</div>

The single-fact endpoint (`POST /v1/facts`) remains for callers that
don't need atomicity.

## Alternatives considered

<div className="stigmem-fields">

<div>
<dt>Alternative</dt>
<dt><span className="stigmem-fields__type">Disposition</span></dt>
<dd>Why</dd>
</div>

<div>
<dt>Client-side compensation only</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>This is the v0.9 OpenClaw adapter's interim approach. Compensations can fail, leaving torn state with no recovery path. The class of bugs surfaces only under load — the worst time to discover them.</dd>
</div>

<div>
<dt>Two-phase commit (prepare + commit)</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>2PC is the right primitive for distributed transactions across multiple nodes; for a single node's writes, it's massive overkill.</dd>
</div>

<div>
<dt>Embed multiple facts inside a single fact value</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>Abuses the data model: each sub-fact loses its own scope, provenance, and audit trail. Each fact is a first-class entity.</dd>
</div>

<div>
<dt>Stream-based ingestion (gRPC bidi, WebSockets)</dt>
<dt><span className="stigmem-fields__type">rejected for v1.0</span></dt>
<dd>Adds substantial protocol surface. Reconsider for v2.0 if a use case emerges where 50-fact batches are insufficient.</dd>
</div>

<div>
<dt>Job queue (async batch processing)</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>Async breaks the synchronous contract adapters depend on. The receiving agent needs to know that when <code>emit_handoff</code> returns, the handoff is durable.</dd>
</div>

</div>

## Consequences

### What gets easier

<div className="stigmem-grid">

<div><h4>Multi-fact operations are reliably consistent</h4><p>Receiving agents see complete or zero state, never torn state.</p></div>
<div><h4>OpenClaw H2 closes structurally</h4><p>The <code>_safe_assert</code> workaround can be removed; the adapter shifts to honest atomicity.</p></div>
<div><h4>Idempotency becomes free</h4><p>Adapters that pass an <code>Idempotency-Key</code> get retry-safe writes.</p></div>
<div><h4>Federation atomicity holds end-to-end</h4><p>Batches replicate as units, preserving consistency across the federation.</p></div>

</div>

### What gets harder

<div className="stigmem-grid">

<div><h4>API surface grows</h4><p>One new endpoint plus supporting concepts (batch_id audit event, idempotency cache).</p></div>
<div><h4>Storage transaction overhead</h4><p>A 50-fact batch holds a write lock longer than 50 individual writes; under contention, slows other writers. Mitigated by bounded batch size.</p></div>
<div><h4>Adapters must migrate</h4><p>v0.9 OpenClaw ships with single-fact + compensation; v0.9.x updates to batch endpoint. Others migrate as they re-emerge through ADR-008.</p></div>

</div>

### New risks

<div className="stigmem-fields">

<div>
<dt>Risk</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Mitigation</dd>
</div>

<div>
<dt><code>R-BATCH-1</code> · batch as DoS vector</dt>
<dt><span className="stigmem-fields__type">mitigated</span></dt>
<dd>A 50-fact batch with deliberate validation failures forces all 50 validations before rollback. Per-fact quotas charge the entire batch even on failure; rate limits cap attempts.</dd>
</div>

<div>
<dt><code>R-BATCH-2</code> · idempotency-key collision</dt>
<dt><span className="stigmem-fields__type">closed</span></dt>
<dd>Idempotency keys are scoped per API key; cross-client collision is not possible.</dd>
</div>

<div>
<dt><code>R-BATCH-3</code> · long batch holds federation latency</dt>
<dt><span className="stigmem-fields__type">tracked</span></dt>
<dd>Replication is asynchronous; the lock is on the local commit, not the federation queue.</dd>
</div>

</div>

## Implementation plan

Targeted for v0.9.x (after the Phase B capability redesign work for
ADR-003 lands; batch and capability handling intersect at validation).

<div className="stigmem-grid">

<div><h4>Server-side</h4><p><code>POST /v1/facts:batch</code> route · transactional commit · idempotency cache · per-fact quota accounting · <code>batch_assert</code> audit event.</p></div>
<div><h4>SDK</h4><p><code>client.assert_facts_batch(facts, idempotency_key=None)</code> method on <code>StigmemClient</code>.</p></div>
<div><h4>Adapter migrations</h4><p>OpenClaw <code>emit_handoff</code> and <code>emit_escalation</code> switch to batch endpoint; compensating retraction removed.</p></div>
<div><h4>Conformance vectors</h4><p>Positive (50 facts atomic) · negative (validation failure mid-batch) · idempotency (replay returns same response).</p></div>
<div><h4>Documentation</h4><p>Build tab API reference; Operate tab notes on batch sizing for performance.</p></div>

</div>

## Open questions

<div className="stigmem-fields">

<div>
<dt>Question</dt>
<dt><span className="stigmem-fields__type">Decision</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Should the batch endpoint support mixed read/write in a single call?</dt>
<dt><span className="stigmem-fields__type">not in v1.0</span></dt>
<dd>Mixed semantics complicate transaction handling. Defer if a use case emerges.</dd>
</div>

<div>
<dt>Should batches be observable via audit log as a single event, or as N events with a shared batch_id?</dt>
<dt><span className="stigmem-fields__type">N events + summary</span></dt>
<dd>N events with shared batch_id, plus one summary <code>batch_assert</code> event. Preserves per-fact audit query patterns while making batch reconstruction possible.</dd>
</div>

</div>

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor
approval rule (founder solo-approval; second contributor sign-off
welcome but not required).*
