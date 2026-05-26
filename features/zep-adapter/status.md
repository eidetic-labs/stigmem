# Zep Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a10` |
| Default surface | `opt-in` |
| Publication state | `published` |
| Package | `stigmem-plugin-zep-adapter` |

The adapter source exists on `main` as experimental design-partner surface
area and is packaged as an opt-in plugin for the v0.9.0a10 adapter publication
batch. Live Zep integration evidence remains design-partner/operator-owned for
v0.1.0.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Zep adapter source and documentation existed as experimental adapter surface area. | `experimental/zep-adapter/STATUS.md`; `experimental/zep-adapter/` |
| `v0.9.0a10` | Packaged as `stigmem-plugin-zep-adapter` v0.1.0 with src-layout package metadata, plugin manifest, tests, and publication projections. | `experimental/zep-adapter/pyproject.toml`; `experimental/zep-adapter/evidence.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for future design-partner review. | Complete | `experimental/zep-adapter/` |
| Unit tests | Mock Zep to validate message formatting, record conversion, session write, query behavior, limits, and error handling. | Complete | `experimental/zep-adapter/tests/test_zep_adapter.py` |
| Package validation | Confirm package metadata, install path, entry point, and dependency compatibility. | Complete | `experimental/zep-adapter/pyproject.toml`; `experimental/zep-adapter/src/stigmem_plugin_zep/manifest.py` |
| Live integration | Validate against Zep Cloud or a self-hosted Zep instance. | Partial | `experimental/zep-adapter/evidence.md` |
| Documentation parity | Feature-owned record plus catalog projections are current. | Complete | This feature record; `experimental/zep-adapter/spec.md` |

## Known Gaps

- Live Zep integration evidence remains operator-owned for v0.1.0.
- The optional bridge depends on external Zep service availability.
- Host applications own session authorization, redaction, retention, and write
  policy.
