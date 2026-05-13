---
title: Security
sidebar_label: Overview
description: Stigmem security posture — threat model risk register, scenarios, security architecture, hardening, and disclosure policy.
audience: Security
sidebar_position: 1
---

# Security

> Per [ADR-005](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/005-docs-ia.md): "Lead Secure with the risk register." This page is the entry point to stigmem's security posture for evaluators, integrators, operators, and security engineers. The threat model and scenarios are the most important artifacts on this page, surfaced first.

---

## Risk register status (v0.9.0a1)

| Status | Count | Description |
|---|---|---|
| **Mitigated** | 10 | mTLS, quotas, key max-age, audit log, replay fuzz, capability tokens, container hardening, and R-19 HLC skew bounds — see the [threat model risk register](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/security/threat-model.md) |
| **Residual** | 1 | Prompt injection (R-05); sanitizer shipped as defense-in-depth while ADR-003 structural separation remains future work |
| **Open** | 7 | R-15 instruction-scope injection, R-16 RTBF DoS, R-17 legal-hold exposure, R-18 CID field-exclusion, R-21 agent feedback-loop worm, R-22 release supply-chain, R-23 admin-level storage tampering |
| **Accepted** | 5 | R-04 at-rest encryption default-off, R-07 Obsidian plugin key storage, R-08 libSQL cloud backend, R-13 cloud embedding data residency, R-20 cloud embedding poisoning |

**The most-severe new structural risk in v0.9.0a1 is R-23** (admin-level storage tampering): an attacker with admin privileges on a stigmem node can — without [ADR-016](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/016-storage-immutability-enforcement.md)'s mitigations — overwrite stored facts, bypassing [ADR-003](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/003-prompt-injection.md)'s prompt-injection trust boundary by silently changing `interpret_as` from `content` to `instruction` at the storage layer. Mitigation is the ADR-016 stack (L1-L5: append-only journal, SQLite triggers, CIDs per [ADR-017](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/017-amendment-to-adr-011-cids-as-core.md), local hash chain, Sigstore Rekor anchor). Targeted: the v0.9.0bN beta series.

The second-priority new risk is R-21 (agent feedback-loop worm). The OpenClaw
adapter remains an experimental alpha connector until its audit blockers close;
handoff-target allowlisting and broader protocol-layer read/write isolation land
in the v0.9.0aN/beta hardening path.

For the full risk register: see the **[Threat Model](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/security/threat-model.md)** (`spec/security/threat-model.md`).

For operator-facing scenarios: see the **[Security Scenarios](./scenarios)**.

For the trust boundary against prompt injection (L1–L6): see [ADR-003](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/003-prompt-injection.md) § Trust boundary.

---

## v0.9.0a1 architectural posture

Per [LIMITATIONS.md §11](https://github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md): the default install of v0.9.0a1 ships with feature-specific code in `node/src/stigmem_node/` for features deferred from v1.0 critical-path scope per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md). The routes are mounted but the features are dormant unless explicitly configured (capability tokens, migrations, manifests). Per [ADR-019](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md) iteration semantics, each v0.9.0aN extracts one cross-cutting feature into a plugin per [ADR-011](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/011-cross-cutting-extraction.md).

Main now includes the 22-hook registry foundation and plugin test harness needed for extraction work. The landed foundation includes typed hook semantics, deterministic manual/core registration, minimum manifest/context/capability APIs, hook-site wiring across assertion, recall, federation, auth, migration, and audit paths, registry audit/metrics plumbing, and benchmark coverage. Production plugin loading, signing enforcement, operator CLI, and per-feature plugin packages remain future alpha-series work.

**For v0.9.0a1 evaluators:** the user-visible default behavior matches v1.0 critical-path scope (single-tenant, no tombstones, no time-travel, no advanced ACL). Architecturally, the cross-cutting code is still in core; that's a known gap with a documented v0.9.0a2..a8 extraction roadmap.

---

## Security architecture

| Page | Topic |
|---|---|
| [Authentication](./authentication.md) | API key auth (Argon2id for new keys; v0.9.0a1 SHA-256 rows rehash on successful use per [ADR-007](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/007-argon2id.md)), expires_at enforcement, session model |
| [Agent keypairs](./agent-keypairs.md) | Ed25519 keypair generation, storage, rotation |
| [Audit log](./audit-log.md) | WAL-ordered audit log, 14 event types, 90-day retention (§22.3) |
| [Audit & quotas](./audit-and-quotas.md) | Per-principal token-bucket quotas, 7 dimensions (§22.4) |
| [Key rotation](./key-rotation.md) | Enforced API key max-age (90d default), Ed25519 rotation runbook (§22.2) |
| [mTLS](./mtls.md) | Federation transport: TLS 1.3 floor, SAN ↔ entity_uri binding (§22.1) |
| [Encryption at rest](./encryption-at-rest.md) | SQLCipher (opt-in for regulated data) |
| [Container hardening](./container-hardening.md) | Distroless, non-root UID 1000, read-only fs, seccomp (§22.6) |

## Operator surfaces

| Page | Topic |
|---|---|
| [Human key issuance](./human-key-issuance.md) | Operator UX for issuing API keys |
| [Human surface](./human-surface.md) | Human-facing operator concerns |
| [Pen-test handbook](./pen-test.md) | Community pen-testing process and reproducer template |

## Disclosure & policy

- **[Compatibility commitment](./compatibility-commitment.md)** — written commitment per [ADR-013](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md).
- **[Security disclosure policy](../community/security-disclosure.md)** — how to report a vulnerability.
- **[SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md)** — supported versions, dependency posture.

## Specification

The protocol specification is the contract security depends on. It lives under Secure per ADR-005:

- **[Specification index](../spec/index.md)** — section navigator with disposition table (which sections are stable in v0.9.0a1, which are deferred to `experimental/<feature>/`).
- **[Canonical spec source](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)** — `spec/stigmem-spec-v0.9.0a1.md`. Section-by-section content review against the `node/` implementation is ongoing.

## Experimental & deferred features

Many features documented in earlier checkpoints are deferred from v0.9.0a1's default install. They live in [`experimental/<feature>/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental). Alpha-series extraction may package some of them as opt-in experimental plugins; promotion into the supported surface requires the [ADR-008](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md) gate process. See **[Experimental & Deferred Features](../reference/experimental-features.md)** for the canonical list.

---

## Quick-start for security researchers

1. Read the **[Threat Model](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/security/threat-model.md)** to understand the trust boundaries and current risk register.
2. Read the **[Security Scenarios](./scenarios)** for operator-facing narratives.
3. Read the **[Pen-test handbook](./pen-test.md)** for the engagement process and reproducer template.
4. Set up a local node via Docker Compose (handbook §4).
5. File private advisories at [github.com/eidetic-labs/stigmem/security/advisories](https://github.com/eidetic-labs/stigmem/security/advisories).
