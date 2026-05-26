# Letta Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a10` |
| Default surface | `opt-in` |
| Publication state | `published` |
| Package | `stigmem-plugin-letta-adapter` |

The adapter source exists on `main` as experimental design-partner surface area
and is packaged as an opt-in plugin for the v0.9.0a10 adapter publication
batch. Live Letta integration evidence remains design-partner/operator-owned
for v0.1.0.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Letta adapter source and documentation existed as experimental adapter surface area. | `experimental/letta-adapter/STATUS.md`; `experimental/letta-adapter/` |
| `v0.9.0a10` | Packaged as `stigmem-plugin-letta-adapter` v0.1.0 with src-layout package metadata, plugin manifest, tests, and publication projections. | `experimental/letta-adapter/pyproject.toml`; `experimental/letta-adapter/evidence.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for future design-partner review. | Complete | `experimental/letta-adapter/` |
| Unit tests | Mock Letta to validate serialization, parsing, environment configuration, push, batch push, pull, filtering, and missing-dependency behavior. | Complete | `experimental/letta-adapter/tests/test_letta_adapter.py` |
| Package validation | Confirm package metadata, install path, entry point, and dependency compatibility. | Complete | `experimental/letta-adapter/pyproject.toml`; `experimental/letta-adapter/src/stigmem_plugin_letta/manifest.py` |
| Live integration | Validate against a real Letta server and agent archival memory. | Partial | `experimental/letta-adapter/evidence.md` |
| Documentation parity | Feature-owned record plus catalog projections are current. | Complete | This feature record; `experimental/letta-adapter/spec.md` |

## Known Gaps

- Live Letta integration evidence remains operator-owned for v0.1.0.
- The optional bridge depends on external Letta server availability.
- Host applications own agent selection, prompt policy, and write policy.
