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
> **Modular spec migration ([ADR-010](../docs/adr/010-modular-specs.md)) is Phase B work.** This document remains a single canonical file through v0.9.0a series; the decomposition into 14 core specs (`spec/specs/01-core.md` through `Spec-14`) lands in Phase B per master-checklist §5.1.

## How to read this document

The spec is divided into core sections (§1–§14, §22, §25 — kept in canonical) and deferred sections (§15–§21, §23, §24 — migrated to per-feature `experimental/<feature>/spec.md`). Cross-references between sections use the per-section anchor convention (`spec/stigmem-spec-v0.9.0a1.md#section-N-M`).

| Section | Title | Status in v0.9.0a1 | Canonical destination |
|---|---|---|---|
| §1 | Motivation | Stable | This file |
| §2 | Atomic fact shape | Stable | This file |
| §3 | Fact semantics | Stable | This file |
| §4 | Intent envelope | **Deferred indefinitely** ([ADR-001](../docs/adr/001-versioning.md)) | `experimental/intent-envelope/spec.md` (placeholder for future reintroduction per ADR-008) |
| §5 | Wire format | Stable | This file |
| §6 | Federation (basic) | Stable | This file |
| §7 | Design decisions log | Stable | This file |
| §8 | Open questions | Stable | This file |
| §9 | Namespace registry | Stable | This file |
| §10 | Schema and migration | Stable | This file |
| §11 | Failure-mode scenarios | Stable | This file |
| §12 | Adapter ABI | Stable | This file |
| §13 | (reserved) | Placeholder | `docs/archive/placeholder-pages/spec/section-13.md` if no real concept; otherwise `experimental/<concept>/` |
| §14 | Lint semantics | Stable | This file |
| §15 | Decay semantics | **Deferred** ([ADR-002](../docs/adr/002-v1-scope.md)) | `experimental/decay/spec.md` |
| §16 | Synthesis | **Deferred** | `experimental/synthesis/spec.md` |
| §17 | Memory garden (basic concept) | Stable; advanced ACL deferred | This file (basic); `experimental/memory-garden-acl/spec.md` (advanced ACL per [ADR-011](../docs/adr/011-cross-cutting-extraction.md)) |
| §18 | Source attestation | **Deferred** | `experimental/source-attestation/spec.md` |
| §19 | Federation trust (capability tokens, manifests, basic) | Stable for the core parts (basic mTLS + capabilities); advanced trust scoring deferred | This file (basic); `experimental/federation-trust-extensions/spec.md` (advanced) |
| §20 | Recall and graph (advanced) | **Deferred** | `experimental/recall-graph/spec.md` |
| §21 | Lazy instruction discovery | **Deferred** | `experimental/lazy-instruction-discovery/spec.md` |
| §22 | Security hardening (mTLS, audit, quotas, container) | Stable | This file |
| §23 | RTBF tombstones | **Deferred** | `experimental/tombstones/spec.md` |
| §24 | Time-travel queries | **Deferred** | `experimental/time-travel/spec.md` |
| §25 | Content-addressed fact IDs (CIDs) | **Stable in core** ([ADR-017](../docs/adr/017-amendment-to-adr-011-cids-as-core.md) — moved from plugin scope back to core) | This file |

## Section status

This file is a skeleton — content arrives section by section as the master-checklist §4.3a per-section review completes. Each migrated section gets a review note documenting:

- What `node/` files were cross-checked against the spec text.
- What discrepancies were found (with issue references for Phase B follow-up).
- What clarity improvements were made.
- What the section's status is (Stable / Experimental / Deferred).

Until a section is migrated, refer to the corresponding section in `spec/archive/evolution/stigmem-spec-v2.0.md` as the most-recent-but-superseded source. The v2.0 snapshot is the most complete pre-reset spec content; review-and-migrate is in progress.

## Cross-references

- [`spec/archive/evolution/`](archive/evolution/) — superseded evolutionary snapshots (`v0.2` through `v2.0`). Each retains a banner pointing here.
- [`spec/EVOLUTION.md`](EVOLUTION.md) — spec-level changelog (renamed from `spec/CHANGELOG.md`).
- [`spec/security/threat-model.md`](security/threat-model.md) — threat model; section references in this spec link to the threat model's risk register.
- [`docs/adr/`](../docs/adr/) — architecture decision records governing the spec evolution.
- [`experimental/<feature>/spec.md`](../experimental/) — per-feature spec content for deferred sections.

---

*This canonical spec lands in PR 2.5 sub-phase 2.5.B. Content migrates incrementally; this file represents the destination structure and the table of section dispositions. The full content arrives across sub-phase 2.5.B commits.*
