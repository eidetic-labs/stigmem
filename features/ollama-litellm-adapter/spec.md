# Ollama/LiteLLM Adapter Spec

## Scope

The Ollama/LiteLLM adapter name refers to using Stigmem tools with local
Ollama models and LiteLLM-supported model strings. The concrete implementation
is the OpenAI-compatible tools adapter under `experimental/openai-tools-adapter`.

This feature covers the legacy Ollama/LiteLLM connector identity and its
mapping to:

- OpenAI-format `tools` declarations exposed by `STIGMEM_TOOLS`;
- `StigmemOpenAIToolsAdapter.tools()` for raw declaration access;
- `StigmemOpenAIToolsAdapter.dispatch(tool_call)` for executing model tool
  calls;
- `run_litellm(model, system_prompt, user_message)` for LiteLLM model strings
  such as `ollama/mistral`;
- `run_openai(model, system_prompt, user_message, base_url, api_key)` for
  OpenAI-compatible endpoints such as local Ollama at `http://localhost:11434/v1`.

## Compatibility Contract

| Surface | Behavior |
| --- | --- |
| Ollama via OpenAI SDK | Use `run_openai()` with a local Ollama `base_url` and non-empty API key placeholder. |
| LiteLLM + Ollama | Use `run_litellm()` with a LiteLLM model string such as `ollama/mistral`. |
| LiteLLM hosted models | Use `run_litellm()` with provider-qualified model strings. |
| Manual dispatch | Use `tools()` and `dispatch()` with OpenAI-compatible chat-completion tool calls. |

## Configuration

| Setting | Purpose |
| --- | --- |
| `STIGMEM_URL` | Stigmem node URL. |
| `STIGMEM_API_KEY` | Optional Stigmem API key. |
| `STIGMEM_SOURCE_ENTITY` | Source entity URI, defaulting to the OpenAI tools adapter source. |

## Non-Goals

- Maintaining a separate Ollama/LiteLLM implementation tree.
- Shipping this adapter as a separate current alpha artifact.
- Certifying specific local model behavior.
- Defining new Stigmem protocol semantics.

## Canonical Spec Assignment

There is no Spec-X assignment for the Ollama/LiteLLM adapter. It is a
compatibility identity for the OpenAI-compatible tools adapter, not a
standalone Stigmem protocol module.
