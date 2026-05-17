---
feature: multi-tenant
spec_id: Spec-X0-Multi-Tenant-Scoping
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-16
owned_risks: []
contributed_risks:
  - R-01
  - R-02
  - R-21
---

# Multi-Tenant Scoping Security

This document is the feature-owned security analysis for
`experimental/multi-tenant/`. It is registered from the unified threat model at
[`spec/security/threat-model.md`](../../spec/security/threat-model.md).

## Owned Risks

None currently identified. Multi-tenant scoping does not own a standalone R-XX
risk in the v0.9.0a1 threat model because the v0.9.0a1 default posture is
single-tenant. If the feature is reintroduced into the supported surface, it
must receive a numbered Spec-X assignment and any tenant-isolation risks must be
registered in the unified threat model.

## Contributed Risks

### R-01: Weak or missing transport peer authentication

R-01 is canonical in
[`spec/security/threat-model.md`](../../spec/security/threat-model.md).
Multi-tenant deployments increase the impact of a transport-authentication
failure because a misbound peer identity can expose or mutate data across
tenant boundaries. Tenant isolation therefore depends on the mTLS SAN to
`entity_uri` binding and federation peer authorization controls already tracked
by the core hardening work.

### R-02: No per-agent or per-tenant quotas

R-02 is canonical in
[`spec/security/threat-model.md`](../../spec/security/threat-model.md). A
multi-tenant node needs quota dimensions that prevent one tenant, agent, or
source from exhausting shared capacity. The feature contributes to this risk by
adding the tenant boundary that quotas must preserve.

### R-21: Agent feedback-loop worm

R-21 is canonical in
[`spec/security/threat-model.md`](../../spec/security/threat-model.md). Tenant
isolation can reduce blast radius only if session provenance and write scopes
remain tenant-aware. Any tenant-crossing recall or write path must preserve the
same-session read/write graph isolation controls.

## Threat Model Delta

Multi-tenant scoping adds a tenant boundary to every read, write, federation,
audit, quota, and background-job path. The feature's security posture depends
on complete tenant propagation: a request must not lose tenant context when it
moves from HTTP routing into storage, hooks, federation, recall, audit, or
plugin code.

The feature is dormant for v0.9.0a1. The current file records the expected
threat-model delta for future reintroduction rather than asserting that
multi-tenant isolation is production-ready today.

## Operator Scenarios

- Do not run untrusted tenants on a single v0.9.0a1 node without an explicit
  feature branch, test evidence, and operator acceptance of the residual risk.
- Treat missing tenant context in logs, audits, or background jobs as a
  security bug.
- Require per-tenant quota evidence before allowing independent tenants to
  share a node.
- Verify that federation peers cannot inject facts into another tenant's
  namespace.

## Conformance Pointers

Required adversarial vectors before promotion:

- every public read and write path enforces tenant isolation;
- audit events include tenant context where tenant context exists;
- quotas can be enforced per tenant as well as per agent/source;
- federation ingest cannot cross tenant boundaries;
- plugin hooks receive tenant context and cannot silently drop it.

## Reintroduction Gates

Gate 1 remains open. Reintroduction requires a numbered Spec-X assignment,
tenant-aware conformance vectors, and an explicit decision on whether
tenant-isolation failures become owned risks or remain mapped to R-01/R-02/R-21.

## Cross-References

- Unified threat model: [`spec/security/threat-model.md`](../../spec/security/threat-model.md)
- Feature status: [`STATUS.md`](STATUS.md)
- Feature concept: [`concept.md`](concept.md)
- Authentication docs: [`docs/docs/security/authentication.md`](../../docs/docs/security/authentication.md)
- ADR-018: [`docs/adr/018-security-documentation-colocation.md`](../../docs/adr/018-security-documentation-colocation.md)
