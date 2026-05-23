# Memory Garden Advanced ACL Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/memory-garden-acl/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/memory-garden-acl/src/stigmem_plugin_memory_garden_acl/manifest.py` | Plugin manifest, capabilities, hooks, and config schema. |
| `experimental/memory-garden-acl/src/stigmem_plugin_memory_garden_acl/config.py` | Operator-controlled gates for advanced ACL behavior. |
| `experimental/memory-garden-acl/src/stigmem_plugin_memory_garden_acl/handlers.py` | Hook placeholders for assertion authorization, recall authorization, and recall filtering. |
| `node/src/stigmem_node/routes/gardens.py` | Core garden CRUD and membership surface that remains outside the plugin. |
| `node/src/stigmem_node/garden_acl.py` | Core helper API for basic garden CRUD, membership, direct read/write guards, and quarantine-garden role checks. |

## v0.9.0a6 Core Boundary Validation

`v0.9.0a6` reconfirms that the basic Memory Garden primitive remains core.
This is intentional: the historical PR4e extraction boundary moved advanced
cross-surface ACL behavior behind `stigmem-plugin-memory-garden-acl` without
removing the protections required for default garden use.

| Core behavior | Disposition | Evidence |
| --- | --- | --- |
| Garden CRUD, slug/UUID lookup, and creator auto-admin membership | Core | `node/tests/routes/test_gardens.py::TestGardenCRUD` |
| Member roster, add/update/remove member operations, duplicate member rejection, and invalid-role rejection | Core | `node/tests/routes/test_gardens.py::TestMembershipAPI` |
| Last-admin removal and demotion protection | Core | `node/tests/routes/test_gardens.py::TestMembershipAPI` |
| Non-member garden read/delete rejection and reader member-management rejection | Core | `node/tests/routes/test_gardens.py::TestGardenACL` |
| Direct `garden_id` fact write enforcement for admin/writer membership | Core | `node/tests/routes/test_gardens.py::TestGardenFactACL` |
| Direct `garden_id` fact query/read enforcement for member access | Core | `node/tests/routes/test_gardens.py::TestGardenFactACL`; `node/tests/conformance/test_conformance_v1.py::TestGardenFactACLConformance` |
| Scope mismatch and missing garden failures | Core | `node/tests/routes/test_gardens.py::TestGardenFactACL`; `node/tests/conformance/test_conformance_v1.py::TestGardenFactACLConformance` |
| Quarantine-garden promote/reject and `quarantine:moderator` role checks | Core under Spec-08, not Memory Garden advanced ACL plugin behavior | `node/tests/routes/test_quarantine.py` |

## v0.9.0a6 Plugin Boundary Validation

The advanced ACL package remains opt-in. Registration alone is not sufficient
to activate advanced behavior; the operator must also set
`STIGMEM_MEMORY_GARDEN_ACL_ENABLED=true` and the specific gate for the behavior
being enabled.

| Plugin behavior | Disposition | Evidence |
| --- | --- | --- |
| Package metadata and `stigmem.plugins` entry point | Opt-in plugin package | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py::test_pyproject_declares_stigmem_plugin_entry_point` |
| Manifest name, version, capabilities, hooks, config schema, and no route mounts | Advanced ACL plugin boundary | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py::test_manifest_declares_expected_boundary` |
| Default config disables all advanced ACL gates | Fail-closed default | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py::test_default_config_keeps_behavior_disabled` |
| Environment config loads explicit operator gates | Operator opt-in | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py::test_config_loads_environment_gates` |
| Hook registration, health, and no-op handler behavior | Registered plugin remains allow/no-op until policy is configured | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py::test_manifest_registers_with_hook_registry` |
| Handler ordering for assertion authorization, recall authorization, and recall filtering | Deterministic plugin/core ordering | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py::test_memory_garden_acl_plugin_hook_order_is_deterministic`; `node/tests/plugins/test_memory_garden_acl_plugin_validation.py::test_memory_garden_acl_hook_ordering_is_deterministic` |
| Advanced OIDC and recall gates require plugin registration and global enablement | No default-install activation | `node/tests/plugins/test_memory_garden_acl_plugin_validation.py::test_advanced_acl_gates_require_plugin_registration`; `node/tests/plugins/test_memory_garden_acl_plugin_validation.py::test_advanced_acl_gates_require_global_enable` |
| Recall filtering activates only with plugin and recall-filter gate | Plugin-loaded advanced behavior | `node/tests/routes/test_gardens.py::TestGardenFactACL::test_plugin_global_query_hides_garden_facts` |
| Default global queries do not apply advanced garden filtering | Default install no-op | `node/tests/routes/test_gardens.py::TestGardenFactACL::test_default_global_query_does_not_apply_advanced_garden_filter` |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py` | Entry point, manifest, config schema, hook declarations, and discovery. |
| Plugin validation | `node/tests/plugins/test_memory_garden_acl_plugin_validation.py` | Registration gates, independent OIDC/recall enablement, and hook ordering. |
| Garden routes | `node/tests/routes/test_gardens.py` | Core garden CRUD, membership, and direct garden fact access behavior. |
| Quarantine routes | `node/tests/routes/test_quarantine.py` | Spec-08 quarantine-garden promote/reject and moderator role behavior retained in core. |
| Protocol conformance | `node/tests/conformance/test_conformance_v1.py` | Garden setup and member/non-member access conformance. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |
| a6 focused core boundary gate | `uv run pytest node/tests/routes/test_gardens.py node/tests/routes/test_quarantine.py node/tests/conformance/test_conformance_v1.py` | 114 passed on 2026-05-23. |
| a6 focused plugin boundary gate | `uv run pytest node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py node/tests/plugins/test_memory_garden_acl_plugin_validation.py node/tests/routes/test_gardens.py::TestGardenFactACL::test_default_global_query_does_not_apply_advanced_garden_filter node/tests/routes/test_gardens.py::TestGardenFactACL::test_plugin_global_query_hides_garden_facts` | 13 passed on 2026-05-23. |

## Coverage Gaps

- Advanced graph-isolation and cross-surface filtering vectors are incomplete.
- External operator soak evidence is not recorded.
- Signed package artifact evidence is deferred until the plugin launch lane.
