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
| `node/src/stigmem_node/garden_acl.py` | Tenant-scoped garden lookup. |
| `node/src/stigmem_node/observability/audit_event.py` | Tenant-scoped audit events. |
| `experimental/multi-tenant/concept.md` | Legacy compatibility pointer for concept links. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_multi_tenant_plugin_scaffold.py` | Entry point, manifest, capabilities, hooks, config gate, identity and metadata tenant resolution, authorization allow decisions, pass-through filters, discovery, and health check. |
| Tenant isolation routes | `node/tests/routes/test_multi_tenant.py` | Default collapse for identity, fact get/query, garden namespace, audit partition, and env-gate behavior; plugin-enabled tenant visibility, garden isolation, slug reuse, cross-tenant write denial, and audit scoping. |
| Garden route coverage | `node/tests/routes/test_gardens.py` | Tenant-aware garden lookup and membership behavior. |
| Observability coverage | `node/tests/observability/test_billing_hooks.py`; `node/tests/observability/test_tracing.py` | Tenant IDs on billing/audit/tracing surfaces. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |

## Coverage Gaps

- Default single-tenant collapse is covered for identity, fact read/query,
  garden lookup/listing, audit listing, and plugin-gate absence. Background
  worker and federation-specific default-collapse checks remain part of the
  cross-surface a8 validation goal.
- No external operator soak evidence is recorded.
- Federation tenant-boundary adversarial vectors are incomplete.
- Per-tenant quota and resource-isolation evidence is incomplete.
- Signed package artifact evidence is deferred until the plugin launch lane.
