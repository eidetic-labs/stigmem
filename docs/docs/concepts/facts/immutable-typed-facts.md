---
title: Why Immutable Typed Facts
sidebar_label: Immutable Typed Facts
sidebar_position: 1
description: Why Stigmem stores knowledge as immutable, typed atomic facts — and why mutable key-value stores fail at federation.
---

# Why Immutable Typed Facts

**Audience:** Protocol implementers and SDK authors.

## The problem

An AI agent needs to remember things — a user's role, a project's status, a preference. The simplest model is a key-value store: `set("alice.role", "CEO")`. But the moment a second agent, a second node, or a second point in time enters the picture, key-value breaks down.

Which write wins? Who wrote it? When? Can you prove the value wasn't tampered with? Can you retract a fact without losing the audit trail? Key-value stores answer none of these questions without bolting on layers of metadata — at which point you've reinvented a fact model, just poorly.

## Naive approaches and why they fail

**Mutable key-value store.** Two agents write different values for the same key. Last-write-wins silently discards one. There is no record of the conflict, no provenance, and no way to know the discarded value ever existed.

**Append-only log.** Better — you keep history. But a flat log has no structure. Querying "what does Alice prefer?" requires scanning the entire log. You also have no way to express typed values, confidence levels, or scope boundaries without inventing ad-hoc conventions that every consumer must understand.

**Document store with versioning.** Git-style versioning preserves history but treats the document as the unit of change. A single-field update creates a full document revision. Merging divergent revisions across federated nodes requires a merge algorithm that understands the document schema — and every schema change breaks the merger.

## Our model

Stigmem stores knowledge as **atomic facts**. Each fact is a single assertion:

```
(entity, relation, value, source, timestamp, hlc, confidence, scope)
```

A fact is immutable once written. Updates are new facts. Retractions are facts with `confidence = 0.0`. This gives you:

| Property | How |
|---|---|
| **Audit trail** | Every assertion ever made is preserved. Nothing is overwritten or deleted. |
| **Typed values** | Seven value types: `string`, `text`, `number`, `boolean`, `datetime`, `ref`, `null` (Spec-01-Fact-Model typed values). |
| **Provenance** | Every fact carries `source` (who asserted it) and `timestamp` (when). |
| **Confidence** | A float in [0.0, 1.0]. `1.0` = certain, `0.5` = uncertain, `0.0` = retracted. |
| **Scope** | `local`, `team`, `company`, or `public` — governs visibility and federation. |
| **Causal ordering** | The HLC field (Spec-12-HLC-Bounded-Skew) gives every fact a causally consistent position in time. |

### Worked example: asserting and retracting a fact

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

Both facts exist in the store. The original assertion is never deleted. Querying `memory:role` for Alice now returns the retraction (confidence 0.0), and any query with `min_confidence > 0` filters it out naturally.

### Entity URI structure

Entities use a formal URI scheme that binds identity to the owning node:

```
stigmem://{authority}/{type}/{id}
```

For example: `stigmem://company.example/user/alice`, `stigmem://company.example/agent/cto`. This prevents identity collisions across federated nodes — two peers can each have a `user/alice` without ambiguity. Entity URIs are normalized to lowercase on ingest (Spec-01-Fact-Model entity normalization) to prevent silent fragmentation.

## Why this is non-obvious

**Immutability seems wasteful.** Storing every version of every fact sounds expensive. But the alternatives — mutable state with conflict resolution, or mutable state with locking — are *more* expensive in a federated system. Immutability eliminates an entire class of distributed systems problems: you never need distributed locks, two-phase commits, or merge algorithms. Contradiction detection (Spec-15-Fact-Semantics) becomes a simple comparison of existing facts.

**Retracting by asserting `confidence = 0.0` seems indirect.** But it preserves the retraction as a first-class event with its own provenance. You can answer "who retracted this, and when?" — which matters for compliance (GDPR Art. 17) and debugging. A `DELETE` operation would destroy that information.

**Seven value types seem arbitrary.** They're the minimum set that covers the practical needs of agent memory systems without requiring schema registration. `string` for labels, `text` for narrative, `number`/`boolean`/`datetime` for structured data, `ref` for entity-to-entity links (which power the graph index in Spec-X11-Recall-Graph graph index), and `null` for explicit "unknown."

## What it costs

- **Storage.** Every update creates a new row. For high-churn relations, the facts table grows proportionally. The decay sweeper (Spec-X9-Decay-Semantics) mitigates this by automatically retracting stale facts based on configurable TTL and half-life policies.
- **Query complexity.** Finding the "current" value for an entity-relation pair requires ordering by HLC and filtering by confidence — not a simple key lookup. The node handles this internally, but implementers should index on `(entity, relation, scope)`.
- **No partial updates.** You can't change one field of a fact. You assert a complete new fact. For the atomic assertions Stigmem models, this is acceptable; for document-shaped data, use `ref`-type values to point to external storage.

## References

- Spec-01-Fact-Model — Atomic Fact Shape
- Spec-01-Fact-Model.1 — FactValue types
- Spec-01-Fact-Model.4 — Hybrid Logical Clock
- Spec-01-Fact-Model.5 — Entity URI Scheme
- Spec-01-Fact-Model.6 — Entity Naming Rules and strict normalizer
- Spec Spec-03-HTTP-API assert-fact route — Assert a fact (wire format)
- Spec Spec-03-HTTP-API retract-fact route — Retract a fact
- Protocol overview and ADRs — Design rationale for immutability
