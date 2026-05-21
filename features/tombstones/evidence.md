# RTBF Tombstones Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/tombstones/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/tombstones/src/stigmem_plugin_tombstones/manifest.py` | Plugin manifest, capabilities, hooks, and migration registration. |
| `experimental/tombstones/src/stigmem_plugin_tombstones/config.py` | Plugin configuration gates. |
| `experimental/tombstones/src/stigmem_plugin_tombstones/handlers.py` | Hook handlers for recall filtering, federation validation, propagation, and migrations. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_tombstone_plugin_scaffold.py` | Entry point, manifest, config, hooks, and migration declaration. |
| Plugin gating | `node/tests/plugins/test_tombstone_plugin_gating.py` | Default-install gating and plugin-loaded behavior. |
| Tombstone behavior | `node/tests/tombstones/` | Filtering, provenance, admin behavior, and tombstone route behavior. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |

## Coverage Gaps

- External operator soak evidence is not recorded.
- Legal-hold and revocation recovery runbooks remain open.
- Federation propagation adversarial evidence is not sufficient for
  graduation.
