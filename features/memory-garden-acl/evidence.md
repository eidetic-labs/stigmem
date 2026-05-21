# Memory Garden Advanced ACL Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/memory-garden-acl/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/memory-garden-acl/src/stigmem_plugin_memory_garden_acl/manifest.py` | Plugin manifest, capabilities, hooks, and config schema. |
| `experimental/memory-garden-acl/src/stigmem_plugin_memory_garden_acl/config.py` | Operator-controlled gates for advanced ACL behavior. |
| `experimental/memory-garden-acl/src/stigmem_plugin_memory_garden_acl/handlers.py` | Hook placeholders for assertion authorization, recall authorization, and recall filtering. |
| `node/src/stigmem_node/routes/gardens.py` | Core garden CRUD and membership surface that remains outside the plugin. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py` | Entry point, manifest, config schema, hook declarations, and discovery. |
| Plugin validation | `node/tests/plugins/test_memory_garden_acl_plugin_validation.py` | Registration gates, independent OIDC/recall enablement, and hook ordering. |
| Garden routes | `node/tests/routes/test_gardens.py` | Core garden CRUD, membership, and direct garden fact access behavior. |
| Protocol conformance | `node/tests/conformance/test_conformance_v1.py` | Garden setup and member/non-member access conformance. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |

## Coverage Gaps

- Advanced graph-isolation and cross-surface filtering vectors are incomplete.
- External operator soak evidence is not recorded.
- Signed package artifact evidence is deferred until the plugin launch lane.
