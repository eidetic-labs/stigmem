# OpenAI Tools Adapter Evidence

## Implementation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/openai-tools-adapter/src/stigmem_plugin_openai_tools/adapter.py` | Implements OpenAI-format tool declarations, dispatch, LiteLLM loop, and OpenAI SDK loop. |
| `experimental/openai-tools-adapter/src/stigmem_plugin_openai_tools/manifest.py` | Exposes the `stigmem.plugins` discovery manifest. |
| `experimental/openai-tools-adapter/pyproject.toml` | Package metadata for `stigmem-plugin-openai-tools-adapter`. |

## Test Evidence

| Path | Evidence |
| --- | --- |
| `experimental/openai-tools-adapter/tests/test_openai_tools_adapter.py` | Unit tests for tool schema shape, environment loading, dispatch, mocked HTTP calls, SDK-object tool calls, and error handling. |
| `experimental/openai-tools-adapter/tests/conftest.py` | Test path setup for importing the src-layout package and workspace SDK/node. |

## Documentation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/openai-tools-adapter/README.md` | Existing setup, usage, model compatibility, and protocol notes. |
| `experimental/openai-tools-adapter/STATUS.md` | ADR-008 gate tracking for the package publication scope. |
| `features/ollama-litellm-adapter/README.md` | Compatibility identity that references this adapter as the behavior owner. |

## Validation Commands

Use the adapter-local mocked tests from the implementation directory:

```bash
uv run ruff check experimental/openai-tools-adapter
uv run pytest experimental/openai-tools-adapter/tests -q
uv build experimental/openai-tools-adapter
```

Use the repository docs checks for feature-record and projection validation:

```bash
python3 scripts/check_feature_records.py
python3 scripts/check_feature_projections.py
python3 scripts/check_feature_security_projection.py
python3 scripts/check_feature_changelog_projection.py
python3 scripts/check_feature_compatibility_projection.py
python3 scripts/check_feature_protocol_projection.py
CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs
```

## Operator-Owned Evidence

- Live LiteLLM provider validation is not complete.
- Live OpenAI SDK provider validation is not complete.
- Local Ollama OpenAI-compatible endpoint validation is not complete.
