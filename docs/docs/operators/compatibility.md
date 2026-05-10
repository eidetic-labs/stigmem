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
| OpenClaw | `stigmem-openclaw>=0.9.0a1`, `stigmem-py>=0.9.0a1,<1.0.0` | OpenClaw runtime ≥1.2 |

## Feature compatibility (v0.9.0a1)

| Feature | Status | Spec | Required versions |
|---|---|---|---|
| Immutable typed facts | Stable | §2, §3 | `node>=0.9.0a1`, `stigmem-py>=0.9.0a1` |
| Scope enforcement | Stable | §3.5 | `node>=0.9.0a1` |
| Two-node mTLS federation | Stable | §22.1, §19 (basic) | `node>=0.9.0a1` |
| Content-addressed fact IDs (CIDs) | Stable in core ([ADR-017](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/017-amendment-to-adr-011-cids-as-core.md)) | §25 | `node>=0.9.0a1` |
| `Stigmem-Version` header | Documented (impl Phase B) | §3 | TBD |
| Argon2id API key hashing | Planned (Phase B per [ADR-007](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/007-argon2id.md)) | §3.5 | TBD |
| Lazy instruction discovery (§21) | Experimental | §21 | [`experimental/lazy-instruction-discovery/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/lazy-instruction-discovery) — targeted v0.9.0a2 |
| RTBF tombstones (§23) | Experimental | §23 | [`experimental/tombstones/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/tombstones) — targeted v0.9.0a5 |
| Time-travel queries (§24) | Experimental | §24 | [`experimental/time-travel/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/time-travel) — targeted v0.9.0a4 |
| Memory garden advanced ACL (§17 advanced) | Experimental | §17 | [`experimental/memory-garden-acl/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/memory-garden-acl) — targeted v0.9.0a6 |
| Source attestation (§18) | Experimental | §18 | [`experimental/source-attestation/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/source-attestation) — targeted v0.9.0a7 |
| Multi-tenant isolation | Experimental | (cross-cutting) | [`experimental/multi-tenant/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/multi-tenant) — targeted v0.9.0a8 |

## Protocol release composition

| Protocol release | Composition |
|---|---|
| `v0.9.0a1` | `stigmem-node@0.9.0a1`, `stigmem-py@0.9.0a1`, `stigmem-openclaw@0.9.0a1`, `stigmem@0.9.0a1` (PyPI) + `@eidetic-labs/stigmem-ts@0.9.0-alpha.1` (npm). Default install matches v1.0 critical-path scope per ADR-002 (single-tenant; no tombstones, time-travel, memory cards, source attestation, or lazy instruction discovery in default behavior). See [LIMITATIONS.md §11](https://github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md) for the architectural-gap acknowledgment. |

## Cross-references

- Source-of-truth YAML: [`docs/compatibility-matrix.yaml`](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/compatibility-matrix.yaml)
- ADR-014: [Compatibility matrix](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/014-compatibility-matrix.md)
- ADR-013: [Deprecation policy](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md)
- [Compatibility commitment](../security/compatibility-commitment.md) — written commitment scaled to v0.9.0a1.
