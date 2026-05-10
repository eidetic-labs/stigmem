---
id: ollama-litellm
title: Ollama / LiteLLM
sidebar_label: Ollama / LiteLLM
audience: Integrator
---

# Stigmem with Ollama and LiteLLM (E6)

**Package:** `stigmem/adapters/openai-tools/adapter.py`

Exposes Stigmem's tools in **OpenAI's function-calling format**, compatible with
[LiteLLM](https://docs.litellm.ai), [Ollama](https://ollama.com) tool-use, and
the OpenAI Python SDK. Use this when your OSS model deployment does not support
MCP but does support the standard `tools` array in chat completion calls.

## Prerequisites

- Python ≥ 3.11
- A running Stigmem node at `STIGMEM_URL`
- `stigmem-py` installed (from the monorepo or `pip install stigmem-py`)
- One or more of:
  - `pip install litellm` (for `run_litellm()`)
  - `pip install openai` (for `run_openai()`)
  - [Ollama](https://ollama.com) with a tool-capable model: `ollama pull mistral`

## Adapter surfaces

| Surface | What it does |
|---|---|
| `STIGMEM_TOOLS` | `list[dict]` of all five Stigmem tools in OpenAI tool-use format |
| `StigmemOpenAIToolsAdapter.tools()` | Same as above via instance method |
| `StigmemOpenAIToolsAdapter.dispatch(tool_call)` | Executes a tool call and returns an OpenAI `{"role": "tool", ...}` message dict |
| `StigmemOpenAIToolsAdapter.run_litellm(model, ...)` | Agentic loop via LiteLLM; accepts any LiteLLM model string |
| `StigmemOpenAIToolsAdapter.run_openai(model, ...)` | Agentic loop via the OpenAI SDK; accepts `base_url` for local Ollama |

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `STIGMEM_URL` | yes | — | Base URL of your Stigmem node |
| `STIGMEM_API_KEY` | no | — | API key if node has `STIGMEM_AUTH_REQUIRED=true` |
| `STIGMEM_SOURCE_ENTITY` | no | `agent:oss` | Entity URI stamped on asserted facts |

## Compatible runtimes

| Runtime | How to use |
|---|---|
| Ollama | `run_openai()` with `base_url="http://localhost:11434/v1"`, `api_key="ollama"` |
| LiteLLM + Ollama | `run_litellm(model="ollama/mistral")` |
| LiteLLM + OpenAI | `run_litellm(model="openai/gpt-4o-mini")` |
| LiteLLM + Anthropic | `run_litellm(model="anthropic/claude-3-5-haiku-20241022")` |
| OpenAI SDK | `run_openai(model="gpt-4o-mini")` |

### Tested Ollama models

| Model | Ollama tag | Tool-use support |
|---|---|---|
| Mistral | `mistral` | ✅ |
| Llama 3.1+ | `llama3.1` | ✅ |
| Qwen 2.5 | `qwen2.5` | ✅ |
| Phi-4 | `phi4` | ✅ |

Pull a model: `ollama pull mistral`

## Usage

### Raw tool declarations — no LLM SDK needed

```python
from adapter import STIGMEM_TOOLS

# Pass to any OpenAI-compatible endpoint
print(STIGMEM_TOOLS[0]["function"]["name"])  # → "assert_fact"
```

### With LiteLLM — Ollama

```python
from adapter import StigmemOpenAIToolsAdapter

adapter = StigmemOpenAIToolsAdapter.from_env()

answer = adapter.run_litellm(
    model="ollama/mistral",
    system_prompt="You are a helpful agent with access to a shared knowledge base.",
    user_message="What role does user:alice have?",
)
print(answer)
```

### With LiteLLM — OpenAI or Anthropic

```python
answer = adapter.run_litellm(
    model="openai/gpt-4o-mini",    # or "anthropic/claude-3-5-haiku-20241022"
    system_prompt="...",
    user_message="...",
)
```

### With the OpenAI SDK against a local Ollama server

```python
from adapter import StigmemOpenAIToolsAdapter

adapter = StigmemOpenAIToolsAdapter.from_env()

answer = adapter.run_openai(
    model="mistral",
    system_prompt="You are a helpful agent.",
    user_message="Assert that user:alice has role engineer.",
    base_url="http://localhost:11434/v1",
    api_key="ollama",   # Ollama ignores this; the SDK requires a non-empty value
)
```

### Manual dispatch loop

```python
import litellm
from adapter import StigmemOpenAIToolsAdapter

adapter = StigmemOpenAIToolsAdapter.from_env()
messages = [
    {"role": "system", "content": "You are an agent with Stigmem access."},
    {"role": "user", "content": "What facts exist about project:loom?"},
]

response = litellm.completion(
    model="ollama/mistral",
    messages=messages,
    tools=adapter.tools(),
)

msg = response.choices[0].message
messages.append(msg.model_dump())

for tc in msg.tool_calls or []:
    messages.append(adapter.dispatch(tc))

# Continue calling litellm.completion() until no tool_calls remain
```

`dispatch()` accepts both SDK objects (`ChatCompletionMessageToolCall`) and plain dicts, so it works from any framework or in tests.

## Running the tests

No live node, Ollama, or API key required — all HTTP is mocked with `respx`.

```bash
cd stigmem
uv run pytest adapters/openai-tools/tests/ -v
```

## Protocol notes

:::note OpenAI type strings are lower-case
The OpenAI format uses `"string"`, `"object"`, `"array"` (lower-case). This is the
opposite of Gemini's upper-case format. If you need both, use each adapter separately.
:::

- `run_litellm()` and `run_openai()` loops cap at `max_rounds=10`.
- Dispatch errors are returned as `{"error": "..."}` in the tool message so the model can reason about failures.

## See also

- [Gemini adapter](./gemini) — Google's `FunctionDeclaration` format
- [MCP server](../../reference/architecture) — for hosts that speak MCP natively (Claude Code, Codex CLI, Cursor, Zed)
