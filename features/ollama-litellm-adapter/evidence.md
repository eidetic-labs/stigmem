# Ollama/LiteLLM Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/openai-tools-adapter/src/stigmem_plugin_openai_tools/adapter.py` | OpenAI-compatible tool declarations, dispatch, LiteLLM loop, and OpenAI SDK loop used by Ollama/LiteLLM. |
| `experimental/openai-tools-adapter/pyproject.toml` | Package metadata for `stigmem-plugin-openai-tools-adapter`. |
| `experimental/ollama-litellm-adapter/concept.md` | Legacy Ollama/LiteLLM connector concept and usage guidance. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/openai-tools-adapter/tests/test_openai_tools_adapter.py` | Tests for OpenAI-format tool declarations, dispatch, mocked HTTP behavior, and error handling. |
| `experimental/openai-tools-adapter/tests/conftest.py` | Test path setup for importing the OpenAI-compatible src-layout package. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/ollama-litellm-adapter/concept.md` | Legacy Ollama/LiteLLM usage and compatible runtime guidance. |
| `experimental/openai-tools-adapter/README.md` | Current behavior, setup, usage, model compatibility, and protocol notes. |
| `experimental/ollama-litellm-adapter/STATUS.md` | Legacy status statement now superseded by this feature record. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Live Ollama and LiteLLM model evidence is not complete.
- The OpenAI-compatible tools adapter feature record owns package publication
  facts; this record remains a historical compatibility identity.
