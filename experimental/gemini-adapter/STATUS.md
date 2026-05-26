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

The adapter source is packaged as an experimental, opt-in plugin for the
v0.9.0a10 adapter publication batch. The package exposes a discovery manifest
and keeps live Gemini API calls under explicit host-application calls.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Gemini adapter source and documentation existed as experimental adapter surface area. | `experimental/gemini-adapter/` |
| `v0.9.0a10` | Packaged as `stigmem-plugin-gemini-adapter` v0.1.0 with src-layout package metadata, plugin manifest, tests, and feature record. | `experimental/gemini-adapter/pyproject.toml`; `experimental/gemini-adapter/evidence.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for design-partner review. | Complete | `experimental/gemini-adapter/` |
| Unit tests | Mock HTTP behavior to validate declarations, environment configuration, dispatch, and error handling. | Complete | `experimental/gemini-adapter/tests/test_gemini_adapter.py` |
| Package validation | Confirm package metadata, install path, entry point, and dependency compatibility. | Complete | `experimental/gemini-adapter/pyproject.toml`; `experimental/gemini-adapter/src/stigmem_plugin_gemini/manifest.py` |
| Live integration | Validate against a real Gemini API key and model. | Partial | `experimental/gemini-adapter/evidence.md` |
| Documentation parity | Feature-owned record plus catalog projections are current. | Complete | `features/gemini-adapter/status.md`; `experimental/gemini-adapter/spec.md` |

## Known Gaps

- Live Gemini API/model validation remains design-partner/operator-owned for
  v0.1.0.
- The optional `run()` loop depends on the external Gemini SDK and API key.
- The adapter returns JSON error payloads to the model loop; host applications
  own redaction and user-facing error policy.
