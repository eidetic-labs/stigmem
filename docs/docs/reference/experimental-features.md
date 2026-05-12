---
title: Experimental Features
sidebar_label: Experimental Features
sidebar_position: 5
audience: Operator
description: "Canonical list of Stigmem features outside the v0.9.0a1 default surface, their risks, constraints, alpha extraction state, and ADR-008 promotion criteria."
---

# Experimental Features

This page is the canonical list of features that exist outside the v0.9.0a1 default surface. Each entry describes the risk, the constraint operators must accept, alpha extraction state where applicable, and the criteria that will promote the feature through the ADR-008 gates.

An EXPERIMENTAL feature may have draft spec text, prototype code, dormant in-core implementation from the pre-reset work, or an opt-in alpha-series plugin package, but it is **not part of the supported default install**. The spec section, wire format, or operational guarantees may change before ADR-008 promotion.

---

## §21 — Lazy Instruction Discovery

**Status:** EXPERIMENTAL  
**Spec page:** [§21 Lazy Instruction Discovery](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/lazy-instruction-discovery/spec.md)

**Risk:** The boot-stub schema and instruction-manifest format are not yet finalized. A mutable or externally-resolvable instruction manifest is a prompt-injection attack surface: if an attacker can influence the manifest URI or cache, they can substitute agent instructions.

**Constraint:** Do not deploy lazy-discovered instructions in production agents handling sensitive data or irreversible tool use until this section reaches GA. Always pin `instructions_manifest_uri` to a trusted, integrity-verified source.

**GA criteria:**
- Boot-stub schema and manifest versioning format stabilized across all spec drafts.
- Manifest signing guarantees cover the URI and cache poisoning attack surface.
- Conformance tests for instruction manifest integrity added to the test suite.

---

## §23 — RTBF Tombstones

**Status:** EXPERIMENTAL  
**Spec page:** [§23 Right-to-be-Forgotten Tombstones](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/tombstones/spec.md)

**Risk:** The tombstone signing format and federation propagation rules are under active security review. The field-exclusion signing pattern may allow federated re-broadcast to produce tombstones that pass local validation but fail downstream signature checks, silently leaving personal data un-erased on remote nodes. This is a compliance risk (GDPR Art. 17, CCPA §1798.105) masked as a cryptography issue.

**Constraint:**
- Do **not** rely on tombstone federation for compliance workflows in multi-node deployments.
- Tombstone `DELETE` operations are locally reliable; cross-node propagation is best-effort.
- Operators with GDPR/CCPA obligations should implement manual deletion coordination across nodes until federation is confirmed correct.

**GA criteria:**
- All spec amendment issues (F1–F11 series) resolved.
- Federation propagation conformance tests passing across 2-node and 4-node topologies.
- Field-exclusion signing pattern validated against adversarial federation scenarios.

---

## §24 — Time-Travel Queries

**Status:** EXPERIMENTAL  
**Spec page:** [§24 Time-Travel / As-Of Queries](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/time-travel/spec.md)

**Risk:** `as_of` queries combined with retroactive tombstone suppression can return data that a tombstone was meant to erase. Isolation semantics differ between SQLite (`BEGIN IMMEDIATE`) and PostgreSQL (`READ COMMITTED`), meaning behavior may silently differ between development and production environments. The `legal_hold` key management path is not yet documented.

**Constraint:**
- Queries at time `T` before a tombstone's `issued_at` may return erased data on some backends. Review your deletion workflow before relying on this for compliance.
- Test your workload on the production backend (not just SQLite in dev).
- `legal_hold` fact handling requires the admin key; do not use this path until key management is documented.

**GA criteria:**
- Tombstone interaction semantics fully specified and conformance-tested across both backends.
- `legal_hold` key management path documented and tested.
- Integration tests for concurrent retraction + `as_of` workloads on both SQLite and PostgreSQL.

---

## §25 — Content-Addressed Fact IDs

**Status:** EXPERIMENTAL  
**Spec page:** [§25 Content-Addressed Fact IDs](../spec/content-addressed-fact-ids.md)

**Risk:** CID-based federation tamper detection is not enforced by default. The 12-month dual-format migration window means CID-less facts from upgraded peers are currently accepted. A MITM attacker on a federated connection can strip CIDs to evade tamper detection.

**Constraint:**
- Do not rely on CID verification as a security control in untrusted federation topologies.
- Set `STIGMEM_REQUIRE_CID=true` in isolated test environments to validate your fact pipeline before enforcement is on by default.

**GA criteria:**
- `STIGMEM_REQUIRE_CID=true` made the default for CID-capable peer connections.
- Full conformance vector suite for on-wire CID presence logic.
- Dual-path migration window formally ended in spec.

---

## Operator warnings (GA features with non-obvious risks)

These features are **GA** but have operational risks that are non-obvious. Each section page carries a callout; the summary is reproduced here for reference.

| Feature | Section | Risk | Required action |
|---------|---------|------|-----------------|
| mTLS (reverse-proxy) | §22.1 | Silent plaintext fallback when TLS terminates at proxy | Set `STIGMEM_MTLS_REQUIRED=true` |
| Source-trust cache | §19.4 | Per-worker incoherence in multi-worker deployments | `STIGMEM_TRUST_CACHE_BACKEND=redis` for production |
| N-node backpressure/scope | §6.7–§6.8 | Draft spec; relay topologies not conformance-tested | Test topology in staging before production |
| Quarantine garden pre-flight | §19.5 | `trust_mode=strict` without quarantine garden permanently drops low-trust facts | Pre-create quarantine garden before enabling strict mode |

---

## Requesting GA promotion

If you are running an experimental feature in production and want to accelerate GA promotion, open an issue in the [stigmem repository](https://github.com/Eidetic-Labs/stigmem) with your topology, workload characteristics, and any anomalies observed. Production data helps prioritize the remaining conformance work.
