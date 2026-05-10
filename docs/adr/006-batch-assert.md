# ADR-006: Batch-assert API for transactional multi-fact writes

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** `stigmem/openclaw/audit.md` H2; OpenClaw adapter v0.9; ADR-002

---

## Context

Several adapter operations write multiple facts as a logical unit: a handoff (handoff_to + handoff_summary + context_refs + continuation), an escalation (escalation + escalate_to + goal), a decision with provenance pointers. These operations are semantically transactional — a partial write produces an inconsistent state that downstream readers cannot detect.

The current API exposes only `POST /v1/facts` for single-fact assertion. Adapters that need to write a multi-fact unit do so by calling the endpoint repeatedly. If any individual write fails, the result is partial state: some facts of the logical unit are written, others are not. The receiving agent boots and sees the partial state with no signal of incompleteness.

The OpenClaw audit (finding H2) documented this gap in concrete code. The v0.9 adapter mitigates by attempting compensating retractions when partial writes are detected, but compensating retractions can themselves fail, leaving torn state. Compensation is a workaround, not a solution.

The right solution is server-side: a batch-assert endpoint with all-or-nothing semantics. This belongs at the API layer, not the adapter layer, because (a) every adapter has the same problem, (b) the SQLite backend already supports transactions natively, and (c) without this, the wire format makes consistent multi-fact writes impossible across the network.

## Decision

We add `POST /v1/facts:batch` with all-or-nothing semantics. The endpoint accepts a list of fact assertions and either commits all of them as a single transaction or returns an error with no facts written.

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

1. **All or nothing.** Either every fact in the batch is written and committed, or none are. The response confirms which case occurred via `facts_written`.

2. **Per-fact validation occurs before any write.** The server validates the entire batch (scope, capability tokens, schema, `interpret_as` rules) before committing any. A validation failure on fact N rejects the whole batch with `failed_at_index: N`.

3. **Single transaction at the storage layer.** SQLite `BEGIN IMMEDIATE` for the duration of the batch; rollback on any error. PostgreSQL backends (deferred to v2.0) use the equivalent transactional primitive.

4. **Idempotency is supported.** A client-supplied `Idempotency-Key` header makes the batch deterministic across retries: if the key has already been processed, the server returns the original response without re-applying. Idempotency keys live in a TTL'd cache (default 24 hours).

5. **Batch size is bounded.** Default `STIGMEM_BATCH_MAX_FACTS = 50`. Operators can tune; larger batches trade latency for transaction-lock duration and are not recommended.

6. **Quotas apply per fact, not per batch.** A 10-fact batch consumes 10 units of the `fact_write` quota. This prevents batch as a quota-bypass surface.

7. **Audit events fire per fact, plus one batch event.** Each fact emits its `fact_write` audit event with the same `batch_id`; an additional `batch_assert` event records the overall batch outcome.

8. **Federation replication treats batches as units.** A batch arriving via federation is replicated as a single unit downstream, preserving the atomicity contract end-to-end.

### Adapter migration

Adapters update to use the batch endpoint where they currently issue multi-fact writes:

- OpenClaw `emit_handoff` → batch-asserts handoff_to, handoff_summary, context_refs, continuation as one unit.
- OpenClaw `emit_escalation` → batch-asserts escalation, escalate_to, goal as one unit.
- Future adapter operations follow the same pattern.

The single-fact endpoint (`POST /v1/facts`) remains for callers that don't need atomicity.

## Alternatives considered

**1. Client-side compensation only (no server-side batch endpoint).** Rejected. This is the v0.9 OpenClaw adapter's interim approach. Compensations can fail, leaving torn state with no recovery path. The class of bugs this produces is exactly the kind that surfaces only under load and operator stress — the worst time to discover them.

**2. Two-phase commit (prepare + commit).** Rejected. 2PC is the right primitive for distributed transactions across multiple nodes; for a single node's writes, it's massive overkill. The batch endpoint is a single-node atomic operation.

**3. Embed multiple facts inside a single fact value (e.g., a fact whose value is a JSON object listing sub-facts).** Rejected. This abuses the data model: each sub-fact loses its own scope, provenance, and audit trail. The whole point of the typed-fact model is that each fact is a first-class entity.

**4. Stream-based ingestion (gRPC bidirectional, WebSockets).** Rejected for v1.0. Adds substantial protocol surface. Reconsider for v2.0 if a use case emerges where 50-fact batches are insufficient.

**5. Implement on top of a job queue (async batch processing).** Rejected. Async processing breaks the synchronous contract that adapters depend on. The receiving agent needs to know that when `emit_handoff` returns, the handoff is durable; an async path makes this hard to reason about.

## Consequences

### What gets easier

- **Multi-fact operations are reliably consistent.** Receiving agents see complete or zero state, never torn state.
- **The OpenClaw H2 audit finding closes structurally.** The `_safe_assert` workaround can be removed; the adapter shifts to honest atomicity.
- **Idempotency becomes free.** Adapters that pass an `Idempotency-Key` get retry-safe writes; adapters that don't, get the existing semantics.
- **Federation atomicity holds end-to-end.** Batches replicate as units, preserving consistency across the federation.

### What gets harder

- **API surface grows.** One new endpoint, plus the supporting concepts (batch_id audit event, idempotency cache). Documented in the Build tab.
- **Storage transaction overhead.** A 50-fact batch holds a write lock longer than 50 individual writes; under contention, this can slow other writers. Mitigated by the bounded batch size.
- **Adapters must migrate.** v0.9 OpenClaw adapter ships with single-fact + compensation; v0.9.x updates to use the batch endpoint. Other adapters in `experimental/` migrate as they re-emerge through ADR-008.

### New risks

- **R-BATCH-1: batch as DoS vector.** A 50-fact batch with deliberate validation failures forces the server to validate all 50 before rolling back. Mitigation: per-fact quotas charge the entire batch even on failure; rate limits cap how often this can be attempted.
- **R-BATCH-2: idempotency-key collision.** Two clients use the same key for different content; the second client gets the first client's response. Mitigation: idempotency keys are scoped per API key; cross-client collision is not possible.
- **R-BATCH-3: long batch holds federation replication latency.** A multi-fact batch in flight delays smaller writes from federating. Mitigation: replication is asynchronous; the lock is on the local commit, not on the federation queue.

## Implementation plan

Targeted for v0.9.x (after the Phase B (capability redesign) capability work for ADR-003 lands; batch and capability handling intersect at validation).

- Server-side: `POST /v1/facts:batch` route, transactional commit, idempotency cache, per-fact quota accounting, `batch_assert` audit event.
- SDK: `client.assert_facts_batch(facts, idempotency_key=None)` method on `StigmemClient`.
- Adapter migrations: OpenClaw `emit_handoff` and `emit_escalation` switch to batch endpoint; compensating retraction code is removed.
- Conformance vectors: positive (50 facts atomic), negative (validation failure mid-batch), idempotency (replay returns same response).
- Documentation: Build tab API reference; Operate tab notes on batch sizing for performance.

## Open questions

- **Should the batch endpoint support mixed read/write in a single call?** Recommended: not in v1.0. Mixed semantics complicate transaction handling. Defer to a follow-up ADR if a use case emerges.

- **Should batches be observable via audit log as a single event with a list, or as N events with a shared batch_id?** Decision: N events with shared batch_id, plus one summary `batch_assert` event. This preserves the existing per-fact audit query patterns while making batch reconstruction possible.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*