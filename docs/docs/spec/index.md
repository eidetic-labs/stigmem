---
id: index
title: Specification
sidebar_label: Overview
---

# Stigmem Protocol Specification

:::note Version
These docs track **Stigmem spec v0.8-draft**. See the [v0.2 docs](/docs/v0.2/spec) for the stable public draft.
:::

The Stigmem specification defines the wire format, fact semantics, and federation protocol for the Stigmem knowledge graph. The authoritative source is `spec/stigmem-spec-v0.8-draft.md` in the repository.

## Spec sections

| Section | Topic | Status in v0.8 |
|---------|-------|----------------|
| §1 | Motivation | Stable |
| §2 | Atomic Fact Shape | Stable |
| §2.1 | FactValue types | Stable |
| §2.2 | FactScope | Stable |
| §2.3 | Reification | Stable |
| §2.4 | Hybrid Logical Clock | Stable (new in v0.5) |
| §3 | Fact Semantics | Stable |
| §4 | Intent Envelope | Stable |
| §5 | Wire Format | Stable |
| §6 | Federation | Stable (extended v0.8 for N-node backpressure) |
| §6.7 | N-node Backpressure Patterns | Draft (new in v0.8) — [guide](/docs/guides/relay-backpressure) |
| §6.8 | Scope Propagation Invariants | Normative (new in v0.8) — [guide](/docs/guides/scope-propagation) |
| §7 | Design Decisions | Stable |
| §8 | Open Questions | Living |
| §9 | Namespace Registry | Stable |
| §10 | Schema and Migration | Stable |
| §11 | Failure Mode Scenarios | Stable (new in v0.5) |
| §12 | Adapter ABI | Stable (new in v0.6) |
| §14 | Lint Semantics | Stable (new in v0.7) |
| §15 | Decay Semantics | Draft (new in v0.8) — [guide](/docs/guides/decay) |
| §16 | Synthesis | Draft (new in v0.8) — [guide](/docs/guides/synthesis) |
| §17 | Memory Garden | Incoming v0.9 |
| §18 | Source Attestation | Incoming v0.9 |

## Key concepts

### Atomic fact shape (§2)

Every fact is a tuple:

```
(entity, relation, value, source, confidence, scope, hlc, timestamp, valid_until?)
```

- **entity** — URI for the subject (e.g. `user:alice`, `stigmem:rel:<uuid>`)
- **relation** — relation URI from the namespace registry (e.g. `memory:prefers`, §9)
- **value** — one of: string, number, boolean, null, text, datetime, ref (§2.1)
- **source** — agent or system that asserted the fact (provenance, §3)
- **confidence** — 0–1 score; confidence=0 is a retraction (§3)
- **scope** — `local | team | company | public` (§2.2); controls federation eligibility
- **hlc** — Hybrid Logical Clock tick for global ordering (§2.4)
- **valid_until** — optional expiry; expired facts excluded from queries by default (§3)

### Hybrid Logical Clock (§2.4)

New in v0.5. Each node maintains an HLC that combines wall-clock time with a monotonic sequence number and a node-ID suffix. Format: `<wall_ms>-<seq>-<node_prefix>`. The HLC ensures total ordering of facts across federated nodes even under clock skew.

### Federation (§6)

Nodes form a peer mesh via the [federation handshake](/docs/guides). Each peer registers with an Ed25519 declaration signature. Replication is pull-based by default: nodes periodically pull from peers using scoped, cursor-paginated requests authenticated with short-lived peer tokens. Conflicts (contradicting facts from different nodes) are stored as first-class records — see the [Conflicts guide](/docs/guides) for resolution strategies.

### Phase 6 operational tools (§15–16)

v0.8 adds three tools for managing fact health over time. They form a pipeline:

| Tool | Spec | Question answered | Guide |
|---|---|---|---|
| `lint_scope` | §14 | "What is wrong with this scope?" | [Lint guide](/docs/guides/) |
| `decay_scope` | §15 | "Apply configured decay policies" | [Decay guide](/docs/guides/decay) |
| `synthesize_scope` | §16 | "What do I currently know?" | [Synthesis guide](/docs/guides/synthesis) |

Both §15 and §16 are **draft** in v0.8. Promotion to normative is a v0.9 goal.

### N-node federation (§6.7–6.8)

v0.8 adds two new subsections to the federation spec:

- **§6.7 N-node Backpressure** — relay lag signals (`X-Stigmem-Replication-Lag` header, HTTP 503 throttle) for multi-hop topologies. See the [relay backpressure guide](/docs/guides/relay-backpressure).
- **§6.8 Scope Propagation Invariants** — closes v0.7 open question §8.5: `company`-scoped facts MUST NOT be re-federated. See the [scope propagation guide](/docs/guides/scope-propagation).

:::info Coming soon
Per-section spec reference pages with full wire format examples are planned for the next docs sprint.
:::
