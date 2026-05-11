---
title: Compatibility Commitment
sidebar_label: Compatibility Commitment
audience: Operator
description: Stigmem's written compatibility commitment per ADR-013 deprecation policy.
---

# Compatibility Commitment

> Per [ADR-013](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md). This document is the written commitment about what stigmem will not break, scaled to project resources and the v0.9.0a1 reset posture.

This commitment is reviewed at every major release. Tightening or loosening goes through an ADR amendment per ADR-001 §Contributor approval rule.

---

## Stability tiers

| Tier | What it means |
|---|---|
| **Stable** | Spec section normative. In production. Eval-covered. No wire-format breaking changes within the v1.x line after v1.0.0 ships. |
| **Beta** | Spec normative; feature-flagged or in early adopters. Minor breaking changes possible before next major release. |
| **Experimental** | Implementation behind a flag, in `experimental/<feature>/`. Spec section may be draft. Breaking changes expected. No compatibility commitment applies. |
| **Deprecated** | Marked for removal. Still operational; replacement available. See removal-distance commitment below. |

## Per-tier commitments

### Stable features

- **Wire format:** No breaking changes within the v1.x line after v1.0.0 ships.
- **Public Python API:** Removing or renaming a public symbol requires a deprecation in v1.x followed by removal no earlier than v2.0.0.
- **Default behavior:** Changing default behavior of a stable feature requires a deprecation cycle.

### Beta features

- Subject to breaking changes in the next minor release with a CHANGELOG entry per change.
- Pin to specific versions; do not rely on a beta feature's wire format being stable across minor releases.

### Experimental features

- Subject to breaking changes in any release without notice.
- Their use behind feature flags is at-your-own-risk.
- Per ADR-008 reintroduction gates, an experimental feature graduates to stable only after passing all five gates.

### Deprecated features

- A feature deprecated in vX.Y is supported through all subsequent vX.* releases.
- Removal may not happen earlier than vX+1.0.
- Operators have at least one major version of notice to migrate.
- The deprecated feature's page carries `removed_in:` and `replacement:` frontmatter; see [Experimental & Deferred Features](../reference/experimental-features.md).

## Wire-format pinning via `Stigmem-Version` header

Per [ADR-012](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/012-version-aware-feature-exposure.md): clients lock to a declared protocol version via the `Stigmem-Version` request header. Server honors the pin; future server versions stay backward-compatible to declared protocol versions for at least one major version after a deprecation lands.

```http
POST /v1/facts HTTP/1.1
Stigmem-Version: 0.9.0a1
Authorization: Bearer <api_key>
Content-Type: application/json

{ ... }
```

The pinning header is documented in spec §3 (Wire Format). Server implementation lands in the v0.9.0bN beta series.x.

## Beta opt-in via `Stigmem-Beta` header

Experimental wire-level features require an opt-in header per call:

```http
POST /v1/facts HTTP/1.1
Stigmem-Version: 0.9.0a1
Stigmem-Beta: instruction-typed-facts
Authorization: Bearer <api_key>
Content-Type: application/json

{ ... }
```

Lists of supported beta names live at `/v1/.well-known/stigmem` in a `betas` field. Beta names retire when the underlying feature graduates per ADR-008 — calls referring to a retired beta name receive `410 Gone` with a deprecation header pointing at the now-stable feature.

## What this commitment does not cover

- **Implementation internals.** Changes to internal Python module structure, algorithm choices, performance characteristics — not subject to the wire-format or public-API commitments above.
- **Operational defaults.** Default rate-limit values, cache TTLs, log retention windows, etc. — operators should pin via configuration, not rely on defaults remaining constant.
- **Pre-1.0 builds.** v0.9.0aN, v0.9.0bN, v1.0.0rcN have NO stability guarantee per ADR-001. Pin to specific versions; auto-upgrade is not safe.
- **Deferred features in `experimental/<feature>/`.** Subject to breaking changes in any release without notice until the feature graduates per ADR-008.

## Cross-references

- [ADR-001](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/001-versioning.md) — versioning, phases, stability commitments.
- [ADR-008](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md) — reintroduction gates.
- [ADR-012](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/012-version-aware-feature-exposure.md) — version-aware feature exposure.
- [ADR-013](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md) — deprecation policy.
- [ADR-014](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/014-compatibility-matrix.md) — compatibility matrix.
- [Experimental & Deferred Features](../reference/experimental-features.md) — current deferred-feature index.
