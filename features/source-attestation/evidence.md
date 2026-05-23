# Source Attestation Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/source-attestation/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/source-attestation/src/stigmem_plugin_source_attestation/manifest.py` | Plugin manifest, capabilities, hooks, and config schema. |
| `experimental/source-attestation/src/stigmem_plugin_source_attestation/config.py` | Plugin configuration gates. |
| `experimental/source-attestation/src/stigmem_plugin_source_attestation/handlers.py` | Hook handlers for assertion validation, recall ranking, and federation inbound validation. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_source_attestation_plugin_scaffold.py` | Entry point, manifest, config, hooks, and discovery. |
| Plugin validation | `node/tests/plugins/test_source_attestation_plugin_validation.py` | Default inert behavior, environment-gate-only no-op behavior, and plugin-loaded source-attestation checks. |
| Assertion enforcement | `node/tests/plugins/test_source_attestation_plugin_scaffold.py` | Normalized direct-source and delegated-source decisions when assertion enforcement is enabled. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |

## Coverage Gaps

- Release artifact signing evidence is not recorded.
- Full key-rotation conformance and API-backed delegation persistence are not complete.
- Federation-source forgery coverage needs to expand before graduation.
