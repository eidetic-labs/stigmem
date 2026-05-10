# Stigmem Spec — Index

This directory contains the canonical specification for the stigmem federated knowledge protocol.

## Canonical spec

**[`stigmem-spec-v0.9.0a1.md`](stigmem-spec-v0.9.0a1.md)** is the canonical specification as of 2026-05-09. Per [ADR-001](../docs/adr/001-versioning.md) + [ADR-019](../docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md), v0.9.0a1 is the first build of stigmem; the version *markers* on earlier evolutionary checkpoints labeled internal development steps, not tagged releases.

The canonical spec is in flight — content arrives section-by-section as the master-checklist §4.3a per-section review completes against actual implementation in `node/`. Until a section is fully migrated, refer to the corresponding section in the v2.0 evolutionary snapshot at [`archive/evolution/stigmem-spec-v2.0.md`](archive/evolution/stigmem-spec-v2.0.md) (the most-complete pre-reset content).

### Section disposition (full table in the canonical spec)

| Section group | Status | Destination |
|---|---|---|
| §1–§14 (core protocol foundation) | Stable in v0.9.0a1 | This file → canonical spec |
| §15 Decay, §16 Synthesis | Deferred per [ADR-002](../docs/adr/002-v1-scope.md) | [`experimental/decay/spec.md`](../experimental/decay/spec.md), [`experimental/synthesis/spec.md`](../experimental/synthesis/spec.md) |
| §17 Memory Garden | Basic concept stable; advanced ACL deferred per [ADR-011](../docs/adr/011-cross-cutting-extraction.md) | Canonical (basic); [`experimental/memory-garden-acl/spec.md`](../experimental/memory-garden-acl/spec.md) (advanced) |
| §18 Source Attestation | Deferred | [`experimental/source-attestation/spec.md`](../experimental/source-attestation/spec.md) |
| §19 Federation Trust | Basic stable (mTLS, capability tokens); advanced trust scoring deferred | Canonical (basic); future `experimental/federation-trust-extensions/spec.md` (advanced) |
| §20 Recall and Graph (advanced) | Deferred | [`experimental/recall-graph/spec.md`](../experimental/recall-graph/spec.md) |
| §21 Lazy Instruction Discovery | Deferred | [`experimental/lazy-instruction-discovery/spec.md`](../experimental/lazy-instruction-discovery/spec.md) |
| §22 Security Hardening | Stable | This file → canonical spec |
| §23 RTBF Tombstones | Deferred | [`experimental/tombstones/spec.md`](../experimental/tombstones/spec.md) |
| §24 Time-Travel Queries | Deferred | [`experimental/time-travel/spec.md`](../experimental/time-travel/spec.md) |
| §25 Content-Addressed Fact IDs (CIDs) | **Stable in core** per [ADR-017](../docs/adr/017-amendment-to-adr-011-cids-as-core.md) | This file → canonical spec |

## Modular spec migration (Phase B work per ADR-010)

Per [ADR-010](../docs/adr/010-modular-specs.md), the spec decomposes into ~14 core specs (`spec/specs/01-core.md` through `Spec-14`) with independent versioning during Phase B. Until that lands, this single canonical file is the spec.

## Evolution

The protocol-spec content evolved through development checkpoints from v0.2 to v2.0. Snapshots preserved at [`spec/archive/evolution/`](archive/evolution/) — see that directory's README. The development-checkpoint changelog is at [`spec/EVOLUTION.md`](EVOLUTION.md) (renamed from `spec/CHANGELOG.md` 2026-05-09 per master-checklist §4.3a). The protocol-release-level changelog going forward is at [`CHANGELOG.md`](../CHANGELOG.md) at repo root.

## Conformance

Conformance vectors at `data/conformance/<spec-version>/` — see `data/conformance/README.md` for the suite layout.

## Cross-references

- [`spec/stigmem-spec-v0.9.0a1.md`](stigmem-spec-v0.9.0a1.md) — canonical spec
- [`spec/EVOLUTION.md`](EVOLUTION.md) — development-checkpoint history
- [`spec/archive/evolution/`](archive/evolution/) — superseded evolutionary snapshots
- [`spec/security/threat-model.md`](security/threat-model.md) — threat model
- [`docs/adr/`](../docs/adr/) — architecture decision records
- [`experimental/<feature>/spec.md`](../experimental/) — per-feature spec content for deferred sections
- [`CHANGELOG.md`](../CHANGELOG.md) — protocol-release-level changelog
- [`ROADMAP.md`](../ROADMAP.md) — public roadmap
