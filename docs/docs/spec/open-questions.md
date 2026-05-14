---
title: Protocol Open Questions
sidebar_label: Open Questions
audience: Spec
description: "Open protocol questions retained for issue and planning follow-up."
---

# Protocol Open Questions {#section-8}

**Status:** Planning and issue-tracking material; not an independent component spec.

Currently-unresolved questions tracked in the spec for community feedback.

**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

1. **Cross-node garden membership.** A garden's members are resolved against the local node's `entity_uri` namespace. In a federated deployment, `stigmem://node-a/user/alice` may be unknown to `node-b`. How should guest membership work across nodes? *Deferred to the pre-reset attestation-chain work federation design.*

2. **Garden-scoped contradiction detection.** Currently contradiction detection operates on `(entity, relation, scope)`. Should `garden_id` be a fourth dimension? Two facts could have the same `(entity, relation, scope)` but different `garden_id` values. *Proposing: contradiction detection remains scope-only; garden isolation means garden-A facts and garden-B facts about the same entity do not contradict each other by default. An opt-in cross-garden contradiction check is a the pre-reset attestation-chain work concern.*

3. **`attested` field and retraction.** If a fact was written in `warn` mode with `attested: false`, should a retraction (same `entity/relation/scope` with `confidence=0.0`) require `enforce` mode to be trusted? *Recommendation: attestation is per-fact, not per-operation. A retraction with `attested: false` is still a valid immutable record; query consumers can filter on `attested`.*

4. **Garden capacity limits.** No current limit on number of gardens or members per garden. Operators should apply application-level limits; a future spec section may add advisory guidance.

---

<details>
<summary>Revisions before v1.0: the pre-reset spec-draft, pre-reset draft</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

**Resolved in pre-reset:**
- ~~§8.1 Entity URI scheme~~ — resolved: formal `stigmem://` scheme normative; informal deprecated with warning (§2.5).
- ~~§8.4 Capability negotiation requirement~~ — resolved: capability negotiation required for federation-enabled nodes (§6.2).

**Resolved in pre-reset:**
- ~~Lint primitive vocabulary~~ — resolved: lint promoted to first-class operation; §14 Lint Semantics normative; `POST /v1/lint` route; `lint_scope` MCP tool.
- ~~Entity fragmentation from case variation~~ — resolved: strict normalizer on ingest (§2.6); case normalization and whitespace collapse applied to `entity` and `source` fields; migration 003 (entity_aliases table) for pre-pre-reset data.

**Resolved in the pre-reset spec:**
- ~~§8.2 Multi-node federation (3+ nodes)~~ — resolved: §6.7 N-node backpressure patterns (draft); §6.8 scope propagation invariants (draft). The N-node model uses pairwise PeerDeclarations; gossip is not required. Relay backpressure and transitive scope enforcement are draft; to be validated by D1 correctness tests before final promotion.
- ~~§8.5 `company`-scoped federation permissiveness~~ — resolved: `company`-scoped facts received from a peer MUST NOT be re-federated to third nodes (§6.8.2). The originating node's grant is non-transitive by default.

**Remaining open:**

1. **Intent envelope wire route.** the pre-reset design work implemented fact model only. Intent envelope wired
   through pre-reset adapters (handoff, escalation, decision facts), but the full
   `IntentEnvelope` wire route is not yet implemented. Deferred to the pre-reset substrate work.

2. **Conflict resolution policy plugins.** Should operators be able to register custom
   resolution functions? Deferred until a concrete use case emerges from the pre-reset design-partner window testing.

3. **Audit log retention.** The federation audit log has no specified retention policy.
   Nodes SHOULD retain at least 7 days (time-based policy is a the pre-reset substrate work concern).

4. **Async lint job API.** The synchronous lint route (§14.5) is sufficient for scopes
   under 100,000 facts. The async job API (`GET /v1/lint/jobs/:job_id`) is specified but
   not yet implemented. the pre-reset substrate work target.

5. **Async decay sweep API.** The synchronous decay sweep (§15.4) is appropriate for
   moderate scope sizes. Async sweep for large scopes (>100,000 facts) follows the lint
   async pattern (§14.5); specified in §15.4 but deferred for implementation.

6. **Fuzzy entity resolver.** Alias-based resolution (§2.6.6) handles canonical URI
   lookup. Semantic similarity matching (e.g. `user:alice` ≡ `user:a.smith`) is
   deferred to the pre-reset substrate work fuzzy resolver (Kompl-style 3-layer matcher).

7. **Synthesis aggregation strategy for contradicted facts.** When `synthesize_scope`
   encounters a contradicted `(entity, relation, scope)` triple, it currently returns
   the highest-confidence value and annotates the output with `contradicted: true`.
   Whether synthesis should surface both values or attempt a weighted merge is an open
   question for the pre-reset substrate work.

---

**From `stigmem-spec-pre-reset draft.md`:**

1. **Cross-node garden membership.** A garden's members are resolved against the local node's `entity_uri` namespace. In a federated deployment, `stigmem://node-a/user/alice` may be unknown to `node-b`. How should guest membership work across nodes? *Deferred to the pre-reset attestation-chain work federation design.*

2. **Garden-scoped contradiction detection.** Currently contradiction detection operates on `(entity, relation, scope)`. Should `garden_id` be a fourth dimension? Two facts could have the same `(entity, relation, scope)` but different `garden_id` values. *Proposing: contradiction detection remains scope-only; garden isolation means garden-A facts and garden-B facts about the same entity do not contradict each other by default. An opt-in cross-garden contradiction check is a the pre-reset attestation-chain work concern.*

3. **`attested` field and retraction.** If a fact was written in `warn` mode with `attested: false`, should a retraction (same `entity/relation/scope` with `confidence=0.0`) require `enforce` mode to be trusted? *Recommendation: attestation is per-fact, not per-operation. A retraction with `attested: false` is still a valid immutable record; query consumers can filter on `attested`.*

4. **Garden capacity limits.** No current limit on number of gardens or members per garden. Operators should apply application-level limits; a future spec section may add advisory guidance.

*(Prior open questions §8.1–§8.6 from the pre-reset spec are unchanged.)*

---

</details>

## Subsection anchors {#subsection-anchors}

*Anchors below are provided so docs links to specific subsections always resolve, even when the subsection text lives only in earlier spec drafts.*

### §8.5 {#section-8-5}
