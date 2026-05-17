---
title: Where Security Analysis Lives
sidebar_label: Where Analysis Lives
description: How Stigmem splits cross-cutting threat-model risks from feature-local experimental security analysis.
audience: Security
sidebar_position: 11
---

# Where Security Analysis Lives

Stigmem uses one protocol-level threat model plus feature-local security files
for experimental features.

## Canonical risk register

The numbered R-XX risk register lives in
[`spec/security/threat-model.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/security/threat-model.md).
Cross-cutting protocol risks stay there. Examples include transport security,
quota enforcement, prompt-injection controls, CID integrity, release
supply-chain integrity, and storage immutability.

## Feature-local security files

Per ADR-018, an experimental feature that owns or materially contributes to a
numbered risk keeps its feature analysis beside the feature:

| Feature | Security analysis | Risk relationship |
|---|---|---|
| Lazy instruction discovery | [`experimental/lazy-instruction-discovery/security.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/lazy-instruction-discovery/security.md) | Owns R-15; contributes to R-21 |
| RTBF tombstones | [`experimental/tombstones/security.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/tombstones/security.md) | Owns R-16 and R-17 |
| Time-travel queries | [`experimental/time-travel/security.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/time-travel/security.md) | Contributes to R-17 and R-18 |
| Memory garden ACL | [`experimental/memory-garden-acl/security.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/memory-garden-acl/security.md) | Contributes to R-21 |
| Source attestation | [`experimental/source-attestation/security.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/source-attestation/security.md) | Contributes to R-22 |
| Multi-tenant scoping | [`experimental/multi-tenant/security.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/multi-tenant/security.md) | Contributes to R-01, R-02, and R-21 |

These files do not replace the risk register. They give operators and
contributors the local threat-model delta, operator scenarios, conformance
pointers, and ADR-008 reintroduction gates for the feature.

## Features without security files

Not every directory under `experimental/` receives a `security.md`
automatically. Adapter, deployment, SDK, dashboard, and workbench directories
remain covered by their `STATUS.md`, contributor checks, and the protocol-level
threat model until they own or materially contribute to a numbered risk. When
that happens, the same PR must add or update the feature-local `security.md`
and cross-link the risk register.

## Contributor rule

When adding a feature-owned R-XX risk:

1. Add the risk to the unified threat model.
2. Add or update `experimental/<feature>/security.md`.
3. Link the risk row in the threat model to the feature-local file.
4. Run the security documentation validator.

```bash
python scripts/check_security_documentation.py
```
