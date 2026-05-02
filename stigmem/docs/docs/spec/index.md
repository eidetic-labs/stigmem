---
id: index
title: Specification
sidebar_label: Overview
---

# Stigmem Protocol Specification

:::note Version
These docs track **Stigmem spec v0.5 (working draft)**. See the [v0.2 docs](/docs/v0.2/spec) for the stable public draft.
:::

The Stigmem specification defines the wire format, fact semantics, and federation protocol for the Stigmem knowledge graph. The authoritative source is `stigmem/spec/stigmem-spec-v0.5-draft.md` in the repository.

## Spec sections

| Section | Topic | Status in v0.5 |
|---------|-------|----------------|
| §1 | Motivation | Stable |
| §2 | Atomic Fact Shape | Stable |
| §2.1 | FactValue types | Stable |
| §2.2 | FactScope | Stable |
| §2.3 | Reification | Stable |
| §2.4 | Hybrid Logical Clock | **New in v0.5** |
| §3 | Fact Semantics | Stable |
| §4 | Intent Envelope | Stable |
| §5 | Wire Format | Stable |
| §6 | Federation | **Promoted to full spec in v0.5** |
| §7 | Design Decisions | Stable |
| §8 | Open Questions | Living |
| §9 | Namespace Registry | Stable |
| §10 | Schema and Migration | Stable |
| §11 | Failure Mode Scenarios | **New in v0.5** |

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

:::info Coming soon
Structured per-section spec reference pages with wire format examples and spec citations are planned for the next docs sprint.
:::
