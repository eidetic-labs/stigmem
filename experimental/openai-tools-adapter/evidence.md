# OpenAI Tools Adapter Evidence

## Validation Scope

This evidence covers the `stigmem-plugin-openai-tools-adapter` v0.1.0 package
publication scope for the `v0.9.0a10` adapter batch.

## Implementation Evidence

| Path | Evidence |
| --- | --- |
| `src/stigmem_plugin_openai_tools/adapter.py` | Implements OpenAI-format tool declarations, dispatch, LiteLLM loop, and OpenAI SDK loop. |
| `src/stigmem_plugin_openai_tools/manifest.py` | Exposes the `stigmem.plugins` discovery manifest. |
| `pyproject.toml` | Package metadata for `stigmem-plugin-openai-tools-adapter`. |

## Test Evidence

| Path | Evidence |
| --- | --- |
| `tests/test_openai_tools_adapter.py` | Unit tests for tool schema shape, environment loading, dispatch, mocked HTTP calls, SDK-object tool calls, and error handling. |
| `tests/conftest.py` | Test path setup for src-layout package and workspace SDK/node imports. |

## Validation Commands

```bash
uv run ruff check experimental/openai-tools-adapter
uv run pytest experimental/openai-tools-adapter/tests -q
uv build experimental/openai-tools-adapter
```

Repository guards:

```bash
python3 scripts/check_security_documentation.py
uv run python scripts/check_plugin_readme_sections.py
uv run python scripts/check_plugin_readme_pypi_consistency.py
uv run python scripts/check_plugin_manifest_version_consistency.py
python3 scripts/check_plugin_publication_disposition.py
python3 scripts/check_feature_records.py
python3 scripts/check_feature_projections.py
python3 scripts/check_feature_security_projection.py
python3 scripts/check_feature_changelog_projection.py
python3 scripts/check_feature_compatibility_projection.py
python3 scripts/check_feature_protocol_projection.py
bash scripts/check.sh contract
bash scripts/check.sh python
```

## Deferred Evidence

- Live LiteLLM provider validation remains operator-owned.
- Live OpenAI SDK provider validation remains operator-owned.
- Local Ollama OpenAI-compatible endpoint validation remains operator-owned.
