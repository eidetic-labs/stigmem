# Lazy Instruction Discovery Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` spec lineage |
| Default surface | `opt-in` |
| Publication state | `hold` - package metadata aligned; registry publication blocked on dry-run evidence and maintainer clearance. |

Lazy instruction discovery source exists on `main` as an experimental plugin
package. Default installs do not expose the lazy-instruction routes unless the
plugin is registered and configured.

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Threat-model delta | R-15 ownership and R-21 contribution. | Blocked on R-15 closure | `features/lazy-instruction-discovery/security.md` |
| ADR | Redesign around ADR-003 capability model. | Blocked | ADR-003 implementation shape. |
| Conformance vectors | Instruction-write, quarantine, recall, namespace isolation. | Partial | Instruction and plugin tests. |
| Operator soak | Non-critical agent workload soak. | Open | None currently recorded. |
| Documentation parity | Boot stub, manifest, operator approval, security docs. | Partial | Package README, source metadata, and feature-owned record are aligned; artifact publication evidence deferred. |

## Known Gaps

- R-15 remains open.
- Admission/promotion policy for instruction-typed facts is incomplete.
- Signed/package artifact evidence is deferred to the plugin launch train.
