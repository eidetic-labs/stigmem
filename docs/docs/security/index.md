---
title: Security
sidebar_label: Overview
description: Security resources for Stigmem — threat model, authentication, transport security, pen-test handbook, and hardening guides.
audience: Operator
sidebar_position: 5
---

# Security

Threat model, authentication, transport security, and compliance controls for Stigmem deployments.

---

## Resources

### [mTLS Federation Transport](./mtls.md)

Configure mutual TLS for Stigmem federation — cert provisioning, zero-downtime rotation, cipher policy (TLS 1.3 / spec §22.1 floor), SAN validation, and Kubernetes cert-manager recipes.

### [Authentication](./authentication.md)

Auth framework — API keys, identity binding, and session management.

### [Agent Keypairs](./agent-keypairs.md)

Ed25519 keypair generation, storage, and rotation for agent identity.

### [OIDC / SSO](./oidc-sso.md)

Integrate enterprise identity providers via OpenID Connect.

### [Encryption at Rest](./encryption-at-rest.md)

Encrypt stored facts and metadata at the storage layer.

### [Audit Log & Per-Principal Quotas](./audit-and-quotas.md)

Mint an `audit.read` API key, query the structured audit log via `GET /v1/admin/audit`, understand the 7 token-bucket quota dimensions and their defaults (spec §22.4.2), and handle 429 backpressure.

### [Container Hardening](./container-hardening.md)

Distroless, non-root, read-only fs container baseline (spec §22.6).

### [Key Rotation](./key-rotation.md)

Rotating encryption and federation keypairs with enforced max-age (spec §22.2).

### [Multi-tenancy](./multi-tenancy.md)

Tenant isolation patterns for shared-node deployments.

### [Source Attestation](./source-attestation.md)

API-key to entity_uri binding with enforce/warn/off modes.

### [Community Pen-Test Handbook](./pen-test.md)

Everything a security researcher needs to run a structured engagement against the Stigmem reference node.

### [Threat Model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md)

Formal threat model — system diagram, STRIDE analysis, and risk register.

### [Disclosure Policy — SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md)

Supported versions and how to report a vulnerability.

---

## Quick-start for reporters

1. **Read the [pen-test handbook](./pen-test.md)** to confirm your target is in scope.
2. **Set up a local node** using Docker Compose (instructions in the handbook §4).
3. **File a private advisory** at [github.com/eidetic-labs/stigmem/security/advisories](https://github.com/eidetic-labs/stigmem/security/advisories).
4. **Include a self-contained reproducer** (handbook §5) and use the report template (handbook §6).
