# Multi-Tenant Scoping Security

## Threat Model Delta

Multi-tenant scoping adds a tenant boundary to reads, writes, federation,
audit, quota, background-job, recall, and plugin paths. The security posture
depends on complete tenant propagation: a request must not lose tenant context
when it moves from HTTP routing into storage, hooks, federation, recall, audit,
or plugin code.

The v0.9.x default posture remains single-tenant. This feature records the
expected security boundary for the opt-in plugin and future reintroduction
decisions; it does not claim multi-tenancy is part of the default supported
surface.

## Owned Risks

None currently identified. If multi-tenant scoping is reintroduced into the
supported surface, tenant-isolation failures must either receive owned R-XX
entries or remain explicitly mapped to protocol-level risks.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-01 weak or missing transport peer authentication | Multi-tenant deployments increase the impact of misbound peer identity because one node may host multiple tenant namespaces. | Preserve mTLS SAN to `entity_uri` binding and federation peer authorization controls. |
| R-02 no per-agent or per-tenant quotas | Shared-node deployments need quota dimensions that prevent one tenant or agent from exhausting shared capacity. | Keep quota accounting tenant-aware and require per-tenant quota evidence before promotion. |
| R-21 agent feedback-loop worm | Tenant isolation can reduce blast radius only if session provenance and write scopes remain tenant-aware. | Preserve same-session read/write graph isolation controls across tenant-scoped recall and write paths. |

## Operator Scenarios

- Do not run untrusted tenants on one node without explicit plugin enablement,
  tenant-boundary test evidence, and acceptance of residual risk.
- Treat missing tenant context in logs, audits, background jobs, or plugin hook
  payloads as a security bug.
- Require per-tenant quota evidence before independent tenants share a node.
- Treat current federation routes as node-level/default-tenant only. They must
  not export non-default tenant facts until tenant-aware federation receives a
  dedicated design, tests, and risk disposition.
- Restrict `/metrics` scrape access on multi-tenant nodes. Prometheus metrics
  include unredacted `tenant=<tenant_id>` labels on audit, fact write, fact
  query, contradiction, and recall counters so operators can maintain
  per-tenant SLOs and incident triage. Any party with scrape access can infer
  tenant inventory and traffic shape. Keep `/metrics` internal, use mTLS or
  token auth when crossing trust boundaries, and prefer opaque tenant IDs when
  tenant inventory is sensitive.
- Enforce tenant naming through API-key registration. Tenant IDs are normalized
  and validated with `validate_tenant_id`: NFKC fold, strip, lowercase, then
  `^[a-z0-9][a-z0-9-]{0,62}$`. Non-conforming tenant IDs fail with
  `tenant_id_empty` or `tenant_id_invalid`.

## Conformance Pointers

Required adversarial vectors before promotion:

- every public read and write path enforces tenant isolation;
- audit events include tenant context where tenant context exists;
- quotas can be enforced per tenant as well as per agent/source;
- federation ingest and egress cannot cross tenant boundaries, or the route is
  explicitly constrained to the default tenant;
- plugin hooks receive tenant context and cannot silently drop it.

## Residual Risk

Gate 1 remains open. Reintroduction requires tenant-aware conformance vectors,
an explicit Spec-X decision, and an explicit risk ownership decision for
tenant-isolation failures.

The v0.9.0a8 disposition for existing federation endpoints is
default-tenant-only. This prevents non-default tenant fact export through
node-level peer replication, but it is not a claim that shared-node,
tenant-aware federation is ready.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
