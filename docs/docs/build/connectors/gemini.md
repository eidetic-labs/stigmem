---
id: gemini
title: Gemini
sidebar_label: Gemini
---

# Stigmem in Gemini (E5)

**Package:** `stigmem/adapters/gemini/adapter.py`

Integrates Stigmem with the [Google Gemini API](https://ai.google.dev) using
Gemini's native `FunctionDeclaration` format. No MCP server required — the
adapter calls the Stigmem node directly over HTTP.

## Prerequisites

- Python ≥ 3.11
- A running Stigmem node at `STIGMEM_URL`
- `stigmem-py` installed (from the monorepo or `pip install stigmem-py`)
- `google-generativeai` installed for the agentic loop: `pip install google-generativeai`

## Adapter surfaces

| Surface | What it does |
|---|---|
| `STIGMEM_FUNCTION_DECLARATIONS` | Ready-to-use `list[dict]` of `FunctionDeclaration`-shaped JSON objects for all five Stigmem tools |
| `StigmemGeminiAdapter.gemini_tools()` | Same as above via instance method |
| `StigmemGeminiAdapter.dispatch(fn_name, fn_args)` | Executes a tool call from a Gemini `FunctionCall` part; returns JSON string |
| `StigmemGeminiAdapter.run(system_prompt, user_message)` | Thin agentic loop that handles the full tool-use turn sequence |

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `STIGMEM_URL` | yes | — | Base URL of your Stigmem node |
| `STIGMEM_API_KEY` | no | — | API key if node has `STIGMEM_AUTH_REQUIRED=true` |
| `STIGMEM_SOURCE_ENTITY` | no | `agent:gemini` | Entity URI stamped on asserted facts |
| `STIGMEM_GEMINI_MODEL` | no | `gemini-2.0-flash` | Gemini model used by `run()` |
| `GOOGLE_API_KEY` | yes (for `run()`) | — | Gemini API key |

## Usage

### Raw declarations — no Gemini SDK needed

```python
from adapter import STIGMEM_FUNCTION_DECLARATIONS

# Pass as plain JSON to any Gemini-compatible REST endpoint
print(STIGMEM_FUNCTION_DECLARATIONS[0]["name"])  # → "assert_fact"
```

### With the Gemini Python SDK

```python
import google.generativeai as genai
from adapter import StigmemGeminiAdapter

genai.configure(api_key="your-gemini-key")
adapter = StigmemGeminiAdapter.from_env()

tool_obj = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(**t)
        for t in adapter.gemini_tools()
    ]
)

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction="You are an agent with access to a shared knowledge base.",
    tools=[tool_obj],
)

chat = model.start_chat()
response = chat.send_message("What facts exist about project:acme-platform?")

# Dispatch any tool calls back to the Stigmem node
for part in response.candidates[0].content.parts:
    if part.function_call:
        result_json = adapter.dispatch(
            part.function_call.name,
            dict(part.function_call.args),
        )
        # wrap result_json in a FunctionResponse and continue the loop
```

### Agentic loop — convenience wrapper

```python
import google.generativeai as genai
from adapter import StigmemGeminiAdapter

genai.configure(api_key="your-gemini-key")
adapter = StigmemGeminiAdapter.from_env()

answer = adapter.run(
    system_prompt="You are a helpful agent with access to a shared knowledge base.",
    user_message="Summarise all active roadmap constraints for project:acme.",
)
print(answer)
```

`run()` handles the full tool-use loop automatically (up to `max_rounds=10`).

## Running the tests

No live node or Gemini key required — all HTTP is mocked with `respx`.

```bash
cd stigmem
uv run pytest adapters/gemini/tests/ -v
```

## Protocol notes

:::note Gemini type strings are upper-case
Gemini uses `"OBJECT"`, `"STRING"`, `"NUMBER"`, `"BOOLEAN"`, `"INTEGER"`, `"ARRAY"`.
This differs from JSON Schema / OpenAI which use lower-case. The adapter handles this
translation — you do not need to adjust tool declarations manually.
:::

- The `run()` loop caps at `max_rounds=10` to prevent infinite tool-call cycles.
- Dispatch errors are returned as `{"error": "..."}` JSON so the model can reason about failures.
- `google-generativeai` is an optional dependency — `STIGMEM_FUNCTION_DECLARATIONS` and `dispatch()` work without it.

## See also

- [OSS adapters (Ollama / LiteLLM)](./ollama-litellm) — OpenAI-compatible format for local models
- [MCP server](../../architecture) — for hosts that do support MCP natively
