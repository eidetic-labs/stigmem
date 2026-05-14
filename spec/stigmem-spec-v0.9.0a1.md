# Stigmem Protocol Specification — v0.9.0a1

**Status:** Canonical (in flight) — section-by-section review of pre-reset spec content against actual implementation in `node/` per master-checklist §4.3a "Spec review and canonicalization to v0.9.0a1."
**Applies to:** Stigmem v0.9.0a1 and reference node implementation.
**Last updated:** 2026-05-09.

> **About this document.** v0.9.0a1 is the first build of stigmem per [ADR-001](../docs/adr/001-versioning.md) + [ADR-019](../docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The protocol-spec content evolved over multiple development checkpoints (snapshots preserved at [`spec/archive/evolution/`](archive/evolution/)). This document is the canonical destination — content is migrated forward from the most-complete pre-reset checkpoint (`stigmem-spec-v2.0.md`), reviewed section-by-section against `node/` implementation, and improved for clarity. Earlier evolutionary snapshots become reference material once a section's content has migrated forward.
>
> **Section status convention** ([ADR-012](../docs/adr/012-version-aware-feature-exposure.md)):
> - `Stable in v0.9.0a1` — committed contract; no breaking changes within v0.9.0a series within the section's wire-format scope.
> - `Experimental in v0.9.0a1` — implementation exists but the section's contract is not committed; reintroduction per [ADR-008](../docs/adr/008-experimental-gates.md) for any section that moves to `experimental/<feature>/spec.md`.
> - `Deferred from v0.9.0a1` — section's content moves to `experimental/<feature>/spec.md` per [ADR-002](../docs/adr/002-v1-scope.md) v1 critical-path scope decision.
>
> **Modular spec migration ([ADR-010](../docs/adr/010-modular-specs.md)) is v0.9.0bN beta-series work.** This document remains a single canonical file through v0.9.0a series; the decomposition into component specs (`spec/specs/01-fact-model.md` through `Spec-14`) lands in the v0.9.0bN beta series.1.

## How to read this document

Per [ADR-010](../docs/adr/010-modular-specs.md), the canonical spec naming convention is `Spec-NN-Topic-Name` for supported protocol component specs and `Spec-XN-Topic-Name` for experimental specs. Until the v0.9.0bN beta series's full per-spec file decomposition lands (master-checklist §5.1), this monolithic file remains canonical and the section-disposition table below uses **`Spec-XN-Name` as the primary identifier** with `[§N legacy]` as a transitional aid for readers familiar with the pre-reset numbering.

The spec is divided into supported protocol components (kept in this canonical file until extraction) and deferred sections (migrated to per-feature `experimental/<feature>/spec.md`).

| Spec ID (target) | Topic | Legacy § | Status in v0.9.0a1 | Canonical destination |
|---|---|---|---|---|
| (protocol overview) | Motivation | §1 | Stable | This file |
| `Spec-01-Fact-Model` | Atomic fact shape | §2 | Stable | `spec/specs/01-fact-model.md` during modular extraction |
| `Spec-01-Fact-Model` + `Spec-02-Scopes-and-ACL` | Fact semantics | §3 | Stable | `Spec-02` scope-enforcement material is in `spec/specs/02-scopes-and-acl.md`; remaining fact-semantics material stays here until extraction |
| (deferred indefinitely) | Intent envelope | §4 | **Deferred indefinitely** ([ADR-001](../docs/adr/001-versioning.md)) | `experimental/intent-envelope/spec.md` (placeholder for future reintroduction per ADR-008) |
| `Spec-03-HTTP-API` | Wire format | §5 | Stable | `spec/specs/03-http-api.md` |
| `Spec-05-Federation-Trust` (basic parts) + `Spec-07-Recall-Pipeline` (basic) | Federation (basic) | §6 | Stable | This file |
| (protocol governance) | Design decisions log | §7 | Stable | This file |
| (protocol governance) | Open questions | §8 | Stable | This file |
| `Spec-01-Fact-Model` + component-specific registries | Namespace registry | §9 | Stable | This file until component prose extraction |
| (storage/migration component, ID TBD) | Schema and migration | §10 | Stable | This file until component spec assignment |
| (conformance/failure-mode component, ID TBD) | Failure-mode scenarios | §11 | Stable | This file until component spec assignment |
| (adapter ABI component, ID TBD) | Adapter ABI | §12 | Stable | This file until component spec assignment |
| (placeholder) | (reserved) | §13 | Placeholder | `docs/archive/placeholder-pages/spec/section-13.md` |
| (lint/conformance component, ID TBD) | Lint semantics | §14 | Stable | This file until component spec assignment |
| (deferred) | Decay semantics | §15 | **Deferred** ([ADR-002](../docs/adr/002-v1-scope.md)) | `experimental/decay/spec.md` |
| (deferred) | Synthesis | §16 | **Deferred** | `experimental/synthesis/spec.md` |
| `Spec-02-Scopes-and-ACL` (basic) + `Spec-X5-Memory-Garden` (advanced) | Memory garden | §17 | Basic Stable; advanced ACL deferred | `spec/specs/02-scopes-and-acl.md` (basic); `experimental/memory-garden-acl/spec.md` (advanced ACL per [ADR-011](../docs/adr/011-cross-cutting-extraction.md)) |
| `Spec-X6-Source-Attestation` | Source attestation | §18 | **Deferred** | `experimental/source-attestation/spec.md` |
| `Spec-04-Manifests` + `Spec-05-Federation-Trust` + `Spec-06-Capability-Tokens` | Federation trust | §19 | Basic Stable; advanced trust scoring deferred | `Spec-04` manifest material is in `spec/specs/04-manifests.md`; remaining basic federation-trust material stays here until extraction; `experimental/federation-trust-extensions/spec.md` (advanced) |
| `Spec-X11-Recall-Graph` | Recall and graph (advanced) | §20 | **Deferred** | `experimental/recall-graph/spec.md` |
| `Spec-X1-Lazy-Instruction-Discovery` | Lazy instruction discovery | §21 | **Deferred** | `experimental/lazy-instruction-discovery/spec.md` |
| `Spec-09-Audit-Log` + `Spec-10-Hardening` + `Spec-11-Replay-Protection` | Security hardening | §22 | Stable | This file |
| `Spec-X2-RTBF-Tombstones` | RTBF tombstones | §23 | **Deferred** | `experimental/tombstones/spec.md` |
| `Spec-X3-Time-Travel` | Time-travel queries | §24 | **Deferred** | `experimental/time-travel/spec.md` |
| `Spec-X4-Content-Addressed-IDs` | Content-addressed fact IDs (CIDs) | §25 | **Stable in core** ([ADR-017](../docs/adr/017-amendment-to-adr-011-cids-as-core.md)). Will be assigned a core `Spec-NN` ID during the modular spec migration; this is a naming/migration step, not ADR-008 graduation. | This file |
| `Spec-12-HLC-Bounded-Skew` | HLC bounded skew (R-19) | (new in v0.9.0a2) | Implemented on main for v0.9.0a2 | This file until modular spec migration |
| `Spec-13-Capability-Based-Instructions` | Capability-based instructions per ADR-003 | (new in v0.9.0bN beta series) | Targeted v0.9.0bN beta series | (the v0.9.0bN beta series) |
| `Spec-14-Batch-Assert` | Batch assert API per ADR-006 | (new in v0.9.0bN beta series) | Targeted v0.9.0bN beta series | (the v0.9.0bN beta series) |
| `Spec-X7-Subscriptions` | Subscriptions / push federation | (new) | **Deferred** | `experimental/subscriptions/spec.md` |

## Section status

This file is a skeleton — content arrives section by section as the master-checklist §4.3a per-section review completes. Each migrated section gets a review note documenting:

- What `node/` files were cross-checked against the spec text.
- What discrepancies were found (with issue references for v0.9.0bN beta-series follow-up).
- What clarity improvements were made.
- What the section's status is (Stable / Experimental / Deferred).

Until a section is migrated, refer to the corresponding section in `spec/archive/evolution/stigmem-spec-v2.0.md` as the most-recent-but-superseded source. The v2.0 snapshot is the most complete pre-reset spec content; review-and-migrate is in progress.

## Cross-references

- [`spec/archive/evolution/`](archive/evolution/) — superseded evolutionary snapshots (`pre-reset` through `v2.0`). Each retains a banner pointing here.
- [`spec/EVOLUTION.md`](EVOLUTION.md) — spec-level changelog (renamed from `spec/CHANGELOG.md`).
- [`spec/security/threat-model.md`](security/threat-model.md) — threat model; section references in this spec link to the threat model's risk register.
- [`docs/adr/`](../docs/adr/) — architecture decision records governing the spec evolution.
- [`experimental/<feature>/spec.md`](../experimental/) — per-feature spec content for deferred sections.

---

*This canonical spec lands in PR 2.5 sub-phase 2.5.B. Content migrates incrementally; this file represents the destination structure and the table of section dispositions. The full content arrives across sub-phase 2.5.B commits.*
