# Memory Garden Advanced ACL Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` spec lineage |
| Default surface | `opt-in` |

Basic garden CRUD, membership, and direct `garden_id` fact read/write guards
remain core. Advanced cross-cutting ACL behavior is extracted into an opt-in
plugin package with registration and operator-controlled gates.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Advanced Memory Garden ACL semantics carried forward as deferred section 17 material. | `spec/stigmem-spec-v0.9.0a1.md` |
| Post-`v0.9.0a1` main | Plugin source package scaffolded with disabled-by-default hooks and validation tests. | `experimental/memory-garden-acl/`; plugin tests |
| `0.9.xA` planned | Continue alpha validation of opt-in plugin behavior and R-21 contribution. | `ROADMAP.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Threat-model delta | Record R-21 contribution and reintroduction blockers. | Partial | `features/memory-garden-acl/security.md` |
| ADR alignment | Preserve deferred advanced ACL and plugin-boundary decisions. | Partial | ADR-002, ADR-008, ADR-010, ADR-011, ADR-020 |
| Conformance vectors | Validate registration gates, explicit opt-in flags, and deterministic hook ordering. | Partial | `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py`; `node/tests/plugins/test_memory_garden_acl_plugin_validation.py` |
| External operator soak | Validate production-like garden isolation workloads. | Open | None currently recorded. |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- No signed or published plugin artifact exists yet.
- Gate 1 remains open until the feature states whether it implements, supports,
  or only coexists with the R-21 read/write graph isolation mitigation.
- External operator soak evidence is not recorded.
