# Multi-Tenant Scoping Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/multi-tenant/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/multi-tenant/src/stigmem_plugin_multi_tenant/manifest.py` | Plugin manifest, capabilities, hooks, and config schema. |
| `experimental/multi-tenant/src/stigmem_plugin_multi_tenant/config.py` | `STIGMEM_MULTI_TENANT_ENABLED` gate. |
| `experimental/multi-tenant/src/stigmem_plugin_multi_tenant/handlers.py` | Tenant resolution, authorization pass-through hooks, federation filter, and migration registration hook. |
| `node/src/stigmem_node/auth.py` | Identity resolution and tenant hook invocation. |
| `node/src/stigmem_node/routes/facts/` | Tenant-scoped fact write, read, query, and provenance behavior. |
| `node/src/stigmem_node/routes/recall/` | Tenant-scoped recall, recall audit, read-scope provenance, metrics, and tracing behavior. |
| `node/src/stigmem_node/routes/federation/replication.py` | Default-tenant-only node-level federation pull/push hook context until tenant-aware federation is designed. |
| `node/src/stigmem_node/subscription_delivery.py` | Tenant-scoped subscription fan-out and delivery sanitizer identity construction. |
| `node/src/stigmem_node/garden_acl.py` | Tenant-scoped garden lookup. |
| `node/src/stigmem_node/observability/audit_event.py` | Tenant-scoped audit events. |
| `experimental/multi-tenant/concept.md` | Legacy compatibility pointer for concept links. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_multi_tenant_plugin_scaffold.py` | Entry point, manifest, capabilities, hooks, config gate, identity and metadata tenant resolution, authorization allow decisions, pass-through filters, discovery, and health check. |
| Plugin validation companion | `node/tests/plugins/test_multi_tenant_plugin_validation.py` | Capability surface, disabled-gate invariance, malformed gate parsing, and tenant-ID normalization. |
| Tenant validation helper | `node/tests/test_tenant_validation.py` | Tenant-ID normalization and rejection rules. |
| Tenant context metadata | `node/tests/test_tenant_context_metadata.py`; `node/tests/lifecycle/test_tenant_resolution_consistency_script.py`; `scripts/check_tenant_resolution_consistency.py` | Every core `TenantContext` construction declares `tenant_context_source`; federation pins are explicitly marked `pinned`. |
| Tenant isolation routes | `node/tests/routes/test_multi_tenant.py` | Default collapse for identity, fact get/query, garden namespace, audit partition, and env-gate behavior; plugin-enabled tenant visibility, recall isolation, recall tracing label propagation, subscription fan-out isolation, garden isolation, slug reuse, cross-tenant write denial, and audit scoping. |
| Federation pull boundary | `node/tests/federation/test_pull.py::TestPullEndpoint::test_non_default_tenant_facts_not_returned_from_node_level_pull` | Existing node-level federation pull exports only default-tenant facts; non-default tenant federation remains deferred. |
| Garden route coverage | `node/tests/routes/test_gardens.py` | Tenant-aware garden lookup and membership behavior. |
| Observability coverage | `node/tests/observability/test_billing_hooks.py`; `node/tests/observability/test_tracing.py`; `node/tests/routes/test_multi_tenant.py` | Tenant IDs on billing/audit/tracing surfaces, including real multi-tenant plugin tenant resolution for billing and route-level recall tracing. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |

## Capability Declaration Scope

The manifest intentionally declares the full multi-tenant namespace surface:
`facts.read`, `facts.write`, `recall.read`, `federation.read`,
`federation.write`, `identity.read`, `tenant.read`, `tenant.write`,
`audit.emit`, and `config.read`. The current load-bearing handlers exercise
tenant resolution, tenant-write acknowledgement, and config validation; the
remaining declarations reserve the namespace for future tenant-aware recall,
federation, audit, and facts hook expansion without changing the plugin
identity on every alpha.

## Core-Enforced, Plugin-Acknowledged Pattern

The v0.9.0a8 isolation boundary is enforced by core request and storage paths.
The plugin promotes a non-default tenant only through `tenant_resolve`; the
authorization and filter hooks acknowledge core-enforced behavior:

- `pre_assert_authorize` and `pre_recall_authorize` return `Allow()` because
  tenant-specific write and recall checks are enforced by core routes and SQL
  filters.
- `recall_filter` returns payloads unchanged after core tenant filtering.
- `federation_outbound_filter` returns payloads unchanged because current
  node-level federation is pinned to the default tenant.
- `migration_register` returns migrations unchanged because tenant compatibility
  columns remain core schema, not plugin-owned migrations.

## Coverage Gaps

- Default single-tenant collapse is covered for identity, fact read/query,
  garden lookup/listing, audit listing, subscription fan-out, federation pull,
  and plugin-gate absence.
- No external operator soak evidence is recorded.
- Tenant-aware federation remains incomplete by design. The current
  node-level federation routes use the default tenant only; non-default tenant
  federation requires a separate design, adversarial vectors, and promotion
  evidence before shared-node readiness can be claimed.
- Per-tenant quota and resource-isolation evidence is incomplete.
- Signed package artifact evidence is deferred until the plugin launch lane.
