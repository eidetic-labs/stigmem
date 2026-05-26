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

The adapter source is packaged as an experimental, opt-in plugin for the
v0.9.0a10 adapter publication batch. The package exposes a discovery manifest
and keeps runtime Cognee access under explicit host-application calls.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Cognee adapter source and documentation existed as experimental adapter surface area. | `experimental/cognee-adapter/` |
| `v0.9.0a10` | Packaged as `stigmem-plugin-cognee-adapter` v0.1.0 with src-layout package metadata, plugin manifest, tests, and feature record. | `experimental/cognee-adapter/pyproject.toml`; `experimental/cognee-adapter/evidence.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for design-partner review. | Complete | `experimental/cognee-adapter/` |
| Unit tests | Mock Cognee to validate serialization, parsing, config, assertion, batch assertion, and query behavior. | Complete | `experimental/cognee-adapter/tests/test_cognee_adapter.py` |
| Package validation | Confirm package metadata, install path, entry point, and dependency compatibility. | Complete | `experimental/cognee-adapter/pyproject.toml`; `experimental/cognee-adapter/src/stigmem_plugin_cognee/manifest.py` |
| Live integration | Validate against a real Cognee runtime, vector store, and LLM backend. | Partial | `experimental/cognee-adapter/evidence.md` |
| Documentation parity | Feature-owned record plus catalog projections are current. | Complete | `features/cognee-adapter/status.md`; `experimental/cognee-adapter/spec.md` |

## Known Gaps

- Live Cognee runtime validation remains design-partner/operator-owned for
  v0.1.0.
- The adapter does not retry Cognee outages internally; callers own retry and
  circuit-breaker policy.
- The adapter stores structured fact text in Cognee and relies on operators to
  choose appropriate Cognee storage, model, and retention settings.
