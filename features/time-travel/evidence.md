# Time-Travel Queries Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/time-travel/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/time-travel/src/stigmem_plugin_time_travel/manifest.py` | Plugin manifest, capabilities, hooks, and config schema. |
| `experimental/time-travel/src/stigmem_plugin_time_travel/config.py` | Environment-backed plugin gates. |
| `experimental/time-travel/src/stigmem_plugin_time_travel/handlers.py` | Hook handlers for authorization, rewrite, audit, and health behavior. |
| `node/src/stigmem_node/routes/facts/query.py` | Fact query `as_of` gating and plugin-loaded behavior. |
| `node/src/stigmem_node/routes/recall/as_of.py` | Historical recall behavior. |
| `node/src/stigmem_node/routes/recall/orchestration.py` | Recall route branch and fail-closed handling. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin package scaffold | `node/tests/plugins/test_time_travel_plugin_scaffold.py` | Entry point, manifest, default config, environment gates, hook registration, deterministic hook order, and discovery. |
| Plugin-loaded behavior | `node/tests/plugins/test_time_travel_plugin_validation.py` | Default install rejects `as_of`; plugin-loaded fact query and recall accept historical reads. |
| Integrated Phase 13 coverage | `node/tests/time_travel/test_phase13_time_travel_cid.py` | Historical fact visibility, retraction, expiry, tombstone, legal-hold, recall, and CID interaction tests. |
| Fast gate | `bash scripts/check.sh python` | Runs plugin, route, and integration tests in the Python check bundle. |

## Conformance and Fixtures

Time-travel conformance is plugin-required. Default conformance must not require
time-travel behavior when `stigmem-plugin-time-travel` is not registered.

## Coverage Gaps

- External operator soak evidence is not recorded.
- Signed/package artifact evidence is deferred.
- Promotion requires additional legal-hold and source-trust/CID integration
  evidence.
