# Ollama/LiteLLM Adapter Security

## Threat Model Delta

The Ollama/LiteLLM adapter identity inherits the OpenAI-compatible tools
adapter threat model: a model can request Stigmem tool calls through
function-calling. Local Ollama deployment reduces hosted-model exposure, while
LiteLLM can route requests to local or hosted providers depending on operator
configuration.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Hosted provider exposure | Operators choose the LiteLLM model string or local Ollama endpoint explicitly. | `experimental/ollama-litellm-adapter/concept.md`; `experimental/openai-tools-adapter/README.md` |
| Unbounded tool loop | The OpenAI-compatible adapter loops cap at `max_rounds`. | `experimental/openai-tools-adapter/README.md`; `experimental/openai-tools-adapter/adapter.py` |
| Dispatch failure leakage | Dispatch errors return JSON error payloads in tool messages. | `experimental/openai-tools-adapter/README.md`; `experimental/openai-tools-adapter/tests/test_openai_tools_adapter.py` |
| API key handling | Stigmem and provider credentials are supplied by environment or SDK configuration, not committed source. | `experimental/openai-tools-adapter/README.md` |

## Residual Risk

- A tool-capable model can attempt reads or writes allowed by the configured
  Stigmem credentials.
- Hosted LiteLLM providers may receive prompt and tool-call context depending
  on model routing.
- Local model tool-use quality depends on the selected Ollama model.
- Live security validation is incomplete because the feature is superseded as
  a standalone implementation.

## Advisories and Findings

None currently recorded for the adapter identity.
