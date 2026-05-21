# Zep Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |

The adapter source exists on `main` as experimental design-partner surface
area. It remains deferred and outside the current alpha artifact set.
Promotion requires an assigned owner, package validation, dependency
validation against a known Zep version, and live integration evidence.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Zep adapter source and documentation existed as experimental adapter surface area. | `experimental/zep-adapter/STATUS.md`; `experimental/zep-adapter/` |
| `0.9.xA` planned | Decide whether to reactivate, replace, or retire the adapter after ownership and integration validation. | `docs/internal/feature-tracker.md`; `docs/compatibility-matrix.yaml` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for future design-partner review. | Complete | `experimental/zep-adapter/` |
| Unit tests | Mock Zep to validate message formatting, record conversion, session write, query behavior, limits, and error handling. | Partial | `experimental/zep-adapter/tests/test_zep_adapter.py` |
| Package validation | Confirm package metadata, install path, and dependency compatibility. | Open | `experimental/zep-adapter/pyproject.toml` |
| Live integration | Validate against Zep Cloud or a self-hosted Zep instance. | Open | None currently recorded. |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- The adapter is not shipped in the current alpha artifact set.
- The feature has no assigned owner.
- Live Zep integration evidence is not complete.
- Dependency, package, and version compatibility evidence are not complete.
