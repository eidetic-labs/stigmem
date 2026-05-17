---
title: Compatibility
sidebar_label: Compatibility
audience: Operator
description: Cross-package compatibility matrix per ADR-014.
---

# Compatibility

Per [ADR-014](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/014-compatibility-matrix.md). The source-of-truth YAML is at [`docs/compatibility-matrix.yaml`](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/compatibility-matrix.yaml). This page renders the YAML as human-readable tables.

> **Initial population at v0.9.0a1 baseline.** The full Docusaurus plugin that auto-renders the YAML at build time is acknowledged as a follow-up; this page is the hand-maintained equivalent for v0.9.0a1 → first publish. Updates ship with every release.

---

## Package versions

| Package | Latest | npm/PyPI |
|---|---|---|
| `stigmem-node` | `0.9.0a1` | PyPI |
| `stigmem-py` | `0.9.0a1` | PyPI |
| `stigmem` (meta-package) | `0.9.0a1` | PyPI |
| `stigmem-openclaw` (adapter) | `0.9.0a1` | PyPI |
| `@eidetic-labs/stigmem-ts` (SDK) | `0.9.0-alpha.1` | npm |
| `stigmem-go` (SDK) | _deferred_ | [`experimental/sdk-go/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/sdk-go) |
| `stigmem-mcp` (adapter) | _deferred_ at 0.4.0 (not aligned) | [`experimental/mcp-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/mcp-adapter) |

## Connector compatibility

| Connector | Stigmem-side requirement | Host-side requirement |
|---|---|---|
| OpenClaw | `stigmem-openclaw>=0.9.0a1`, `stigmem-py>=0.9.0a1,<1.0.0`; experimental alpha connector only. Public copy/framing corrections are queued for the v0.9.0a2 artifact refresh. | OpenClaw runtime ≥1.2 |

## Feature compatibility (v0.9.0a1)

| Feature | Status | Spec | Required versions |
|---|---|---|---|
| Immutable typed facts | Stable | `Spec-01-Fact-Model`, `Spec-15-Fact-Semantics` | `node>=0.9.0a1`, `stigmem-py>=0.9.0a1` |
| Scope enforcement | Stable | `Spec-02-Scopes-and-ACL` | `node>=0.9.0a1` |
| Two-node mTLS federation | Stable | `Spec-10-Hardening`, `Spec-05-Federation-Trust` | `node>=0.9.0a1` |
| Content-addressed fact IDs (CIDs) | Stable in core ([ADR-017](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/017-amendment-to-adr-011-cids-as-core.md)) | `Spec-21-Content-Addressed-IDs` | `node>=0.9.0a1` |
| `Stigmem-Version` header | Documented (implementation in the v0.9.0bN beta series) | `Spec-03-HTTP-API` | `node>=0.9.0bN` (planned) |
| Argon2id API key hashing | Planned (the v0.9.0bN beta series per [ADR-007](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/007-argon2id.md)) | `Spec-03-HTTP-API` | `node>=0.9.0bN` (planned) |
| Lazy instruction discovery | Experimental | `Spec-X1-Lazy-Instruction-Discovery` | [`experimental/lazy-instruction-discovery/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/lazy-instruction-discovery) — targeted v0.9.0a2 |
| RTBF tombstones | Experimental | `Spec-X2-RTBF-Tombstones` | [`experimental/tombstones/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/tombstones) — source-only on `main`; no released plugin artifact yet |
| Time-travel queries | Experimental | `Spec-X3-Time-Travel-Queries` | [`experimental/time-travel/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/time-travel) — targeted v0.9.0a4 |
| Memory garden advanced ACL | Experimental | `Spec-X5-Memory-Garden-Advanced-ACL` | [`experimental/memory-garden-acl/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/memory-garden-acl) — source-only on `main`; no released plugin artifact yet |
| Source attestation | Experimental | `Spec-X6-Source-Attestation` | [`experimental/source-attestation/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/source-attestation) — source-only on `main`; no released plugin artifact yet |
| Multi-tenant isolation | Experimental | (cross-cutting) | [`experimental/multi-tenant/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/multi-tenant) — targeted v0.9.0a8 |

## Protocol release composition

| Protocol release | Composition |
|---|---|
| `v0.9.0a1` | `stigmem-node@0.9.0a1`, `stigmem-py@0.9.0a1`, `stigmem-openclaw@0.9.0a1`, `stigmem@0.9.0a1` (PyPI) + `@eidetic-labs/stigmem-ts@0.9.0-alpha.1` (npm). Default install matches v1.0 critical-path scope per ADR-002 (single-tenant; no tombstones, time-travel, memory cards, source attestation, or lazy instruction discovery in default behavior). OpenClaw/ClawHub is available for alpha evaluation only and remains subject to [LIMITATIONS.md §9](https://github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md#9-running-the-openclaw-bundled-adapter-as-is). See [LIMITATIONS.md §11](https://github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md) for the architectural-gap acknowledgment. |

## Cross-references

- Source-of-truth YAML: [`docs/compatibility-matrix.yaml`](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/compatibility-matrix.yaml)
- ADR-014: [Compatibility matrix](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/014-compatibility-matrix.md)
- ADR-013: [Deprecation policy](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md)
- [Compatibility commitment](../security/compatibility-commitment.md) — written commitment scaled to v0.9.0a1.
