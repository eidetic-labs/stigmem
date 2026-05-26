# Zep Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `src/stigmem_plugin_zep/adapter.py` | Zep client configuration, fact-to-message encoding, Zep session write, query, and record conversion. |
| `src/stigmem_plugin_zep/manifest.py` | Plugin discovery manifest for `stigmem-plugin-zep-adapter` v0.1.0. |
| `demo.py` | Optional demonstration flow that asserts a Stigmem fact, mirrors it into Zep, and reads extracted facts. |
| `pyproject.toml` | Package metadata, optional Zep/demo extras, entry point, and build configuration. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `tests/test_zep_adapter.py` | Mocked Zep tests for message formatting, record shape, session writes, query behavior, limit handling, scope stamping, and Zep error handling. |
| `tests/conftest.py` | Test path setup for importing the src-layout adapter package and workspace dependencies. |

## Validation

| Command | Expected result |
| --- | --- |
| `uv run ruff check experimental/zep-adapter` | Adapter lint passes. |
| `uv run pytest experimental/zep-adapter/tests -q` | Mocked Zep unit tests pass. |
| `uv build experimental/zep-adapter` | Source distribution and wheel build. |
| `python3 scripts/check_security_documentation.py` | Experimental security docs validate. |
| `uv run python scripts/check_plugin_readme_sections.py` | Published plugin README sections validate. |
| `uv run python scripts/check_plugin_manifest_version_consistency.py` | Plugin manifest version matches package metadata. |

## Evidence Gaps

- Live Zep Cloud or self-hosted Zep evidence remains operator-owned for v0.1.0.
- Session authorization, redaction, retention, and deduplication policy are
  caller-owned integration concerns.
