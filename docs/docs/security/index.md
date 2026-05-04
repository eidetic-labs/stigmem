---
id: security
title: Security
sidebar_label: Security
description: Security resources for Stigmem — threat model, community pen-test handbook, disclosure policy, and hardening guides.
---

# Security

This section collects Stigmem's security resources for operators, researchers, and contributors.

---

## Resources

### [Community Pen-Test Handbook](./pen-test.md)

Everything a security researcher needs to run a structured engagement against the Stigmem reference node — in-scope surfaces, safe-harbor terms, reproducer expectations, the report template, severity guidance, the 90-day disclosure timeline, and the recognition model.

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
- Audit log surface — 13 event types, 90-day retention (§22.3)
- Per-principal quotas — token-bucket model across 7 dimensions (§22.4)
- Replay protection fuzz tests (§22.5)
- Container baseline — distroless, non-root, read-only fs (§22.6)

Known pre-Phase-12 gaps are listed in the [pen-test handbook §10](./pen-test.md#10-known-hardening-gaps) and the [threat model risk register](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md#7-risk-register).
