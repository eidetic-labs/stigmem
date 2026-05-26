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

The adapter source is packaged as an experimental, opt-in plugin for the
v0.9.0a10 adapter publication batch. The package exposes a discovery manifest
and keeps live Letta access under explicit host-application calls.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Letta adapter source and documentation existed as experimental adapter surface area. | `experimental/letta-adapter/` |
| `v0.9.0a10` | Packaged as `stigmem-plugin-letta-adapter` v0.1.0 with src-layout package metadata, plugin manifest, tests, and feature record. | `experimental/letta-adapter/pyproject.toml`; `experimental/letta-adapter/evidence.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Source preservation | Keep the adapter source available for design-partner review. | Complete | `experimental/letta-adapter/` |
| Unit tests | Mock Letta to validate serialization, parsing, environment configuration, push, batch push, pull, filtering, and missing-dependency behavior. | Complete | `experimental/letta-adapter/tests/test_letta_adapter.py` |
| Package validation | Confirm package metadata, install path, entry point, and dependency compatibility. | Complete | `experimental/letta-adapter/pyproject.toml`; `experimental/letta-adapter/src/stigmem_plugin_letta/manifest.py` |
| Live integration | Validate against a real Letta server and agent memory. | Partial | `experimental/letta-adapter/evidence.md` |
| Documentation parity | Feature-owned record plus catalog projections are current. | Complete | `features/letta-adapter/status.md`; `experimental/letta-adapter/spec.md` |

## Known Gaps

- Live Letta server validation remains design-partner/operator-owned for
  v0.1.0.
- The adapter does not retry Letta outages internally; callers own retry and
  circuit-breaker policy.
- Host applications own agent selection and write policy.
