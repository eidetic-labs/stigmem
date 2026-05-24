# Cognee Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `dormant` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |
| Publication state | `defer` - unowned design-partner adapter; live Cognee and dependency validation are not complete. |

The adapter source exists on `main` as experimental design-partner surface
area. It remains dormant and outside the current alpha artifact set. Promotion
requires an assigned owner, package validation, dependency validation against a
known Cognee version, and live integration evidence.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Cognee adapter source and documentation existed as experimental adapter surface area. | `experimental/cognee-adapter/STATUS.md`; `experimental/cognee-adapter/` |
| `0.9.xA` planned | Decide whether to reactivate, replace, or retire the adapter after ownership and integration validation. | `docs/internal/feature-tracker.md`; `docs/compatibility-matrix.yaml` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for future design-partner review. | Complete | `experimental/cognee-adapter/` |
| Unit tests | Mock Cognee to validate serialization, parsing, config, assertion, batch assertion, and query behavior. | Partial | `experimental/cognee-adapter/tests/test_cognee_adapter.py` |
| Package validation | Confirm package metadata, install path, and dependency compatibility. | Open | `experimental/cognee-adapter/pyproject.toml` |
| Live integration | Validate against a real Cognee runtime, vector store, and LLM backend. | Open | None currently recorded. |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- The adapter is not shipped in the current alpha artifact set.
- The feature has no assigned owner.
- Live Cognee integration evidence is not complete.
- Dependency, package, and version compatibility evidence are not complete.
