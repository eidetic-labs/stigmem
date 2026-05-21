# Gemini Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |

The adapter source exists on `main` as experimental model/tooling adapter
surface area. It remains deferred and outside the current alpha artifact set.
Promotion requires an assigned owner, package validation, dependency
validation against a known Gemini SDK/API version, and live integration
evidence.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Gemini adapter source and documentation existed as experimental adapter surface area. | `experimental/gemini-adapter/STATUS.md`; `experimental/gemini-adapter/` |
| `0.9.xA` planned | Decide whether to reactivate, replace, or retire the adapter after ownership and integration validation. | `docs/internal/feature-tracker.md`; `docs/compatibility-matrix.yaml` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for future model/tooling review. | Complete | `experimental/gemini-adapter/` |
| Unit tests | Mock HTTP and adapter behavior to validate declarations, environment configuration, dispatch, and error handling. | Partial | `experimental/gemini-adapter/tests/test_gemini_adapter.py` |
| Package validation | Confirm package metadata, install path, and dependency compatibility. | Open | `experimental/gemini-adapter/pyproject.toml` |
| Live integration | Validate against a real Gemini API key and model. | Open | None currently recorded. |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- The adapter is not shipped in the current alpha artifact set.
- The feature has no assigned owner.
- Live Gemini integration evidence is not complete.
- Dependency, package, and version compatibility evidence are not complete.
