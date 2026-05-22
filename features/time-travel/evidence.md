# Time-Travel Queries Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/time-travel/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/time-travel/src/stigmem_plugin_time_travel/manifest.py` | Plugin manifest, capabilities, hooks, and config schema. |
| `experimental/time-travel/src/stigmem_plugin_time_travel/config.py` | Environment-backed plugin gates. |
| `experimental/time-travel/src/stigmem_plugin_time_travel/handlers.py` | Hook handlers for authorization, rewrite, audit, and health behavior. |
| `node/src/stigmem_node/routes/time_travel_gate.py` | Shared fail-closed gate requiring both plugin registration and explicit operator enablement before `as_of` routes run. |
| `node/src/stigmem_node/routes/facts/query.py` | Fact query `as_of` gating and plugin-loaded behavior. |
| `node/src/stigmem_node/routes/recall/as_of.py` | Historical recall behavior. |
| `node/src/stigmem_node/routes/recall/orchestration.py` | Recall route branch and fail-closed handling. |
| `node/src/stigmem_node/federation/federation_ingest.py` | R-18 `valid_until` extension rejection before historical reads can observe extended federated metadata. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin package scaffold | `node/tests/plugins/test_time_travel_plugin_scaffold.py` | Entry point, manifest, default config, environment gates, hook registration, deterministic hook order, and discovery. |
| Plugin-loaded behavior | `node/tests/plugins/test_time_travel_plugin_validation.py` | Default install rejects `as_of`; registered-but-disabled plugin rejects `as_of`; separate fact-query and recall gates are honored; explicitly enabled plugin-loaded fact query and recall accept historical reads. |
| Integrated Phase 13 coverage | `node/tests/time_travel/test_phase13_time_travel_cid.py` | Historical fact visibility, retraction, expiry, retroactive tombstone suppression, legal-hold oracle suppression, recall, retention-floor errors, historical recency scoring, CID tamper rejection, and source-trust-style rank-hook visibility tests. |
| Admin capability voting consistency | `node/tests/time_travel/test_admin_capability_voting_consistency.py` | Fact-query and recall `as_of` paths both use `Identity.is_admin()` so a `capability_check` voter can consistently deny admin legal-hold visibility. |
| Federation `valid_until` extension rejection | `node/tests/federation/test_valid_until_extension.py` | First observation, idempotent replay, extension rejection, shrinkage no-op, `None` handling, timezone equivalence, and audit evidence for `federation_valid_until_extension_rejected`. |
| Fast gate | `bash scripts/check.sh python` | Runs plugin, route, and integration tests in the Python check bundle. |

## Conformance and Fixtures

Time-travel conformance is plugin-required. Default conformance must not require
time-travel behavior when `stigmem-plugin-time-travel` is not registered.

## Coverage Gaps

- External operator soak evidence is not recorded.
- Signed/package artifact evidence is deferred.
- Operator-facing source-trust policy evidence remains deferred to the
  source-attestation feature record.
