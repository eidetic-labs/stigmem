# Cognee Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a10` |
| Default surface | `opt-in` |
| Publication state | `published` |
| Package | `stigmem-plugin-cognee-adapter` |

The adapter source exists on `main` as experimental design-partner surface
area. As of v0.9.0a10, it is packaged as an opt-in plugin with src-layout
metadata, a Stigmem discovery manifest, and mock-based validation evidence.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Cognee adapter source and documentation existed as experimental adapter surface area. | `experimental/cognee-adapter/STATUS.md`; `experimental/cognee-adapter/` |
| `v0.9.0a10` | Package as `stigmem-plugin-cognee-adapter` v0.1.0 for adapter batch publication. | `experimental/cognee-adapter/pyproject.toml`; `experimental/cognee-adapter/evidence.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for future design-partner review. | Complete | `experimental/cognee-adapter/` |
| Unit tests | Mock Cognee to validate serialization, parsing, config, assertion, batch assertion, and query behavior. | Complete | `experimental/cognee-adapter/tests/test_cognee_adapter.py` |
| Package validation | Confirm package metadata, install path, entry point, and dependency compatibility. | Complete | `experimental/cognee-adapter/pyproject.toml`; `experimental/cognee-adapter/src/stigmem_plugin_cognee/manifest.py` |
| Live integration | Validate against a real Cognee runtime, vector store, and LLM backend. | Partial | `experimental/cognee-adapter/evidence.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | Complete | This feature record; `experimental/cognee-adapter/spec.md` |

## Known Gaps

- Live Cognee integration evidence remains design-partner/operator-owned for
  v0.1.0.
- The adapter does not retry Cognee outages internally; callers own retry and
  circuit-breaker policy.
- Dataset isolation, LLM provider selection, and retention policy remain
  operator responsibilities.
