# Time-Travel Queries Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` spec lineage |
| Default surface | `opt-in` |

Time-travel query source exists on `main` as an experimental plugin package.
The default install rejects `as_of` requests unless the plugin is registered.
This validates the ADR-011 plugin boundary without graduating time-travel into
the default supported surface.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Spec lineage carried section 24 time-travel semantics. | `spec/stigmem-spec-v0.9.0a1.md` |
| Post-`v0.9.0a1` main | Source package and fail-closed behavior landed for alpha validation. | `experimental/time-travel/`; plugin tests |
| `v0.9.0a4` active | Active release target for time-travel extraction validation, default fail-closed behavior, plugin-loaded `as_of` coverage, and release-surface alignment. | `ROADMAP.md`; `docs/internal/releases/v0.9.0a4-roadmap.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Threat-model delta | Record contributed risks and reintroduction blockers. | Partial | `features/time-travel/security.md` |
| ADR alignment | Preserve experimental and plugin-boundary decisions. | Partial | ADR-008, ADR-010, ADR-011, ADR-020 |
| Conformance vectors | Split default fail-closed and plugin-loaded behavior. | Partial | `node/tests/plugins/test_time_travel_plugin_validation.py`; `node/tests/time_travel/test_phase13_time_travel_cid.py` |
| External operator soak | Validate production-like workloads. | Open | None currently recorded. |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- No signed or published plugin artifact exists yet.
- Legal-hold and CID/source-trust integration need additional promotion
  evidence before graduation.
- Operator documentation for historical legal-hold access remains incomplete.
- Artifact publication evidence is deferred until the planned plugin set is
  ready for release packaging.
