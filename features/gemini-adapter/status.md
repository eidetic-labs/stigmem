# Gemini Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a10` |
| Default surface | `opt-in` |
| Publication state | `published` |
| Package | `stigmem-plugin-gemini-adapter` |

The adapter source exists on `main` as experimental model/tooling adapter
surface area and is packaged as an opt-in plugin for the v0.9.0a10 adapter
publication batch. Live Gemini API/model validation remains
design-partner/operator-owned for v0.1.0.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Gemini adapter source and documentation existed as experimental adapter surface area. | `experimental/gemini-adapter/STATUS.md`; `experimental/gemini-adapter/` |
| `v0.9.0a10` | Packaged as `stigmem-plugin-gemini-adapter` v0.1.0 with src-layout package metadata, plugin manifest, tests, and publication projections. | `experimental/gemini-adapter/pyproject.toml`; `experimental/gemini-adapter/evidence.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for future model/tooling review. | Complete | `experimental/gemini-adapter/` |
| Unit tests | Mock HTTP and adapter behavior to validate declarations, environment configuration, dispatch, and error handling. | Complete | `experimental/gemini-adapter/tests/test_gemini_adapter.py` |
| Package validation | Confirm package metadata, install path, entry point, and dependency compatibility. | Complete | `experimental/gemini-adapter/pyproject.toml`; `experimental/gemini-adapter/src/stigmem_plugin_gemini/manifest.py` |
| Live integration | Validate against a real Gemini API key and model. | Partial | `experimental/gemini-adapter/evidence.md` |
| Documentation parity | Feature-owned record plus catalog projections are current. | Complete | This feature record; `experimental/gemini-adapter/spec.md` |

## Known Gaps

- Live Gemini integration evidence remains operator-owned for v0.1.0.
- The optional `run()` loop depends on external Gemini SDK/API availability.
- Host applications own prompt redaction and write policy before dispatch.
