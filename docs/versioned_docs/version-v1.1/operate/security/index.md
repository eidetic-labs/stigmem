---
id: security
title: Security
sidebar_label: Security
description: Security resources for Stigmem — threat model, community pen-test handbook, disclosure policy, and hardening guides.
audience: Operator
---

# Security

This section collects Stigmem's security resources for operators, researchers, and contributors.

---

## Resources

### [Community Pen-Test Handbook](./pen-test.md)

Everything a security researcher needs to run a structured engagement against the Stigmem reference node — in-scope surfaces, safe-harbor terms, reproducer expectations, the report template, severity guidance, the 90-day disclosure timeline, and the recognition model.

### [mTLS Federation Transport](./mtls.md)

Configure mutual TLS for Stigmem federation — cert provisioning, zero-downtime rotation, cipher policy (TLS 1.3 / §22.1 floor), SAN validation, and Kubernetes cert-manager recipes.

### [Audit Log & Per-Principal Quotas](./audit-and-quotas.md)

Mint an `audit.read` API key, query the structured audit log via `GET /v1/admin/audit`, understand the 7 token-bucket quota dimensions and their defaults (§22.4.2), tune write/read ceilings via environment variables, and handle 429 backpressure with `Retry-After`.

### [Threat Model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md)

The formal threat model for the Stigmem reference node and federated protocol. Covers the system diagram, all eight trust boundaries, STRIDE analysis per boundary, and a risk register linked to spec sections §19, §20, and §22.

### [Disclosure Policy and Current Posture — SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md)

Supported versions, how to report a vulnerability (GitHub private advisory), and the security posture of the current release (Dependabot triage, audit tooling, controls in effect).

---

## Quick-start for reporters

1. **Read the [pen-test handbook](./pen-test.md)** to confirm your target is in scope.
2. **Set up a local node** using Docker Compose (instructions in the handbook §4).
3. **File a private advisory** at [github.com/eidetic-labs/stigmem/security/advisories](https://github.com/eidetic-labs/stigmem/security/advisories). Do not open a public issue.
4. **Include a self-contained reproducer** (handbook §5) and use the report template (handbook §6).

---

## Phase 12 hardening status

Phase 12 is shipping the security hardening layer defined in spec §22:

- mTLS for federation (§22.1)
- Key rotation with enforced max-age (§22.2)
- [Audit log surface — 13 event types, 90-day retention (§22.3)](./audit-and-quotas.md)
- [Per-principal quotas — token-bucket model across 7 dimensions (§22.4)](./audit-and-quotas.md#per-principal-quotas-224)
- Replay protection fuzz tests + constant-time crypto audit (§22.5) — **complete**
- Container baseline — distroless, non-root, read-only fs (§22.6)

Known pre-Phase-12 gaps are listed in the [pen-test handbook §10](./pen-test.md#10-known-hardening-gaps) and the [threat model risk register](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md#7-risk-register).

---

## §22.5 — Constant-time crypto audit notes

**Scope reviewed:** all Python source under `node/src/` and `sdks/stigmem-py/src/`.

**Methodology:** static AST sweep for `==` / `!=` on secret-adjacent variable names
(`check_constant_time.py`, run in CI as step CT001), plus manual review of all
signature-verification paths.

### Findings

| ID | Location | Vulnerability class | Severity | Status |
|----|----------|---------------------|----------|--------|
| CT-1 | `identity/capability.py` (private-key cache check) | Timing oracle on private-key seed comparison | Low / not exploitable (neither operand attacker-controlled) | Fixed — replaced `==` with `hmac.compare_digest` |

**All signature verifications** (`Ed25519PublicKey.verify()`, `jwt.decode()` via PyJWT)
use the `cryptography` C library's constant-time comparison internally. No Python-level
`==` comparison against signature bytes, MACs, or digests was found in the auth paths.

**Peer-token nonce replay** is enforced via `nonce_cache` DB lookup in `peer_auth.py`
(not a byte comparison — the DB query raises `nonce_already_seen` on hit). The property
is fuzz-tested in `node/tests/test_phase12_replay_fuzz.py` with Hypothesis.

### Residual risk

- Native-layer timing in `libsodium` / OpenSSL (used by the `cryptography` package) is
  out of scope for Python-layer review. Both libraries implement constant-time Ed25519
  by design; no action required.
- The CT001 lint rule catches only variable-name-based heuristics. Novel variable names
  for secret material would evade it. Quarterly manual review recommended.

### Regression prevention

`scripts/check_constant_time.py` runs on every CI push (step **CT001 constant-time
comparison lint**) and exits non-zero on any new violation. Add `# nosec CT001` to
suppress confirmed non-secrets with an explanatory comment.
