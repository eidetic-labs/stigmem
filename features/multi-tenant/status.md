# Multi-Tenant Scoping Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a8` extraction target |
| Default surface | `opt-in` |

Multi-tenant scoping exists on `main` as an opt-in experimental plugin source
package. Default installs collapse callers into the `default` tenant. Plugin
registration plus `STIGMEM_MULTI_TENANT_ENABLED=true` preserves non-default
tenant resolution.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a8` planned | Multi-tenant isolation extraction into an opt-in experimental plugin completes the planned alpha extraction train. | `ROADMAP.md` |
| Post-extraction main | Plugin source package, default-collapse behavior, plugin-enabled tenant isolation, and route/plugin tests landed. | `experimental/multi-tenant/`; `node/tests/routes/test_multi_tenant.py`; `node/tests/plugins/test_multi_tenant_plugin_scaffold.py` |
| `0.9.xA` planned | Continue alpha validation and decide whether a future Spec-X assignment is needed. | `ROADMAP.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Threat-model delta | Record R-01, R-02, and R-21 contributions. | Partial | `features/multi-tenant/security.md` |
| ADR alignment | Preserve default-surface exclusion and plugin-boundary decisions. | Partial | ADR-002, ADR-008, ADR-009, ADR-011, ADR-020 |
| Conformance vectors | Validate default collapse and plugin-enabled tenant isolation. | Partial | `node/tests/routes/test_multi_tenant.py`; `node/tests/plugins/test_multi_tenant_plugin_scaffold.py` |
| External operator soak | Validate shared-node deployments with independent tenants. | Open | None currently recorded. |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- No signed or published plugin artifact exists yet.
- No numbered Spec-X assignment exists.
- Gate 1 remains open until tenant-isolation failures are either assigned
  owned risks or remain explicitly mapped to R-01, R-02, and R-21.
- External operator soak evidence is not recorded.
