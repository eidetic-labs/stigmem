# Zep Adapter Status

**Status:** active experimental adapter package
**Package:** `stigmem-plugin-zep-adapter`
**Version:** `0.1.0`
**Default surface:** opt-in
**Release line:** `v0.9.0a10`

The Zep adapter is packaged as an opt-in bridge between Stigmem facts and Zep
session memory. It is discoverable through the `stigmem.plugins` entry-point
group after installation, but it has no node-global behavior gate and performs
no work unless a host application imports and calls the adapter.

## Gate Tracking

| Gate | Status | Evidence |
| --- | --- | --- |
| Source layout | Complete | `src/stigmem_plugin_zep/adapter.py`; `src/stigmem_plugin_zep/manifest.py` |
| Package metadata | Complete | `pyproject.toml`; `uv build experimental/zep-adapter` |
| Unit tests | Complete | `tests/test_zep_adapter.py` |
| Security review | Complete for mocked/package scope | `security.md`; `features/zep-adapter/security.md` |
| Live integration | Operator-owned | Zep Cloud/self-hosted validation is outside v0.1.0 package publication. |

## Publication Scope

Included:

- src-layout Python package metadata;
- plugin discovery manifest;
- mocked Zep client tests;
- feature-owned spec, status, evidence, security, and changelog updates;
- public plugin catalog and compatibility projections.

Not included:

- live Zep Cloud or self-hosted Zep acceptance evidence;
- session authorization policy;
- redaction, retention, or deduplication controls beyond documented caller
  ownership.
