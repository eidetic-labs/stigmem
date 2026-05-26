# OpenAI Tools Adapter Spec

The OpenAI tools adapter maps Stigmem client operations into the
OpenAI-compatible `tools` array and tool-result message format. It is intended
for model runtimes that support OpenAI-style function calling but do not use
MCP directly.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `STIGMEM_TOOLS` | Static list of five OpenAI-format tool declarations. |
| `tools()` | Returns `STIGMEM_TOOLS` for direct use with chat-completion APIs. |
| `dispatch(tool_call)` | Executes a single tool call from a dict or SDK object and returns an OpenAI-format tool message. |
| `run_litellm(model, system_prompt, user_message)` | Runs a bounded LiteLLM tool loop using the adapter declarations and dispatch surface. |
| `run_openai(model, system_prompt, user_message, base_url, api_key)` | Runs a bounded OpenAI SDK tool loop, including OpenAI-compatible local endpoints. |

## Tool Declarations

The adapter exposes these Stigmem operations:

| Tool | Backing client operation |
| --- | --- |
| `assert_fact` | `StigmemClient.assert_fact()` |
| `query_facts` | `StigmemClient.query()` |
| `resolve_contradiction` | `StigmemClient.resolve_conflict()` |
| `subscribe_scope` | `StigmemClient.query()` scoped to a subscription-style request |
| `lint_scope` | `StigmemClient.lint()` |

Tool schemas use lower-case JSON Schema type strings because OpenAI-compatible
tool calling expects JSON Schema casing. This intentionally differs from the
Gemini adapter's native `FunctionDeclaration` format.

## Runtime Configuration

| Setting | Purpose |
| --- | --- |
| `STIGMEM_URL` | Required by `from_env()`; points at the Stigmem API. |
| `STIGMEM_API_KEY` | Optional API key passed to `StigmemClient`. |
| `STIGMEM_SOURCE_ENTITY` | Optional source entity; defaults to `agent:openai-tools`. |
| `max_rounds` | Tool-loop bound for LiteLLM and OpenAI SDK helpers; defaults to `10`. |

## Compatibility

- LiteLLM model strings such as `ollama/mistral` can use `run_litellm()`.
- Hosted provider strings supported by LiteLLM can use the same loop when
  credentials are configured outside this repository.
- OpenAI-compatible local endpoints can use `run_openai()` with `base_url`.
- The Ollama/LiteLLM adapter feature record is a compatibility identity that
  points at this adapter for behavior and test evidence.

## Out of Scope

- MCP transport or protocol negotiation.
- Provider-specific model certification.
- Shipping provider SDKs in the default alpha artifact set.
- Maintaining a second Ollama/LiteLLM implementation separate from this
  OpenAI-compatible adapter.

## Spec Assignment

The canonical feature spec assignment is `Spec-X7-OpenAI-Tools-Adapter`. The
adapter is an external integration spec around existing Stigmem fact/query
behavior, not a new core protocol module.
