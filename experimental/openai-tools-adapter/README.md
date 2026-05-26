# Stigmem OpenAI-Compatible Tool-Use Adapter

Package: `stigmem-plugin-openai-tools-adapter`

Exposes Stigmem's tools in **OpenAI's function-calling format** - compatible
with [LiteLLM](https://docs.litellm.ai), [Ollama](https://ollama.com) tool-use,
and the OpenAI Python SDK.  Use this when your OSS model deployment does not
support MCP but does support the standard `tools` array in chat completion calls.

## Design

The adapter has four surfaces:

1. **`tools()`** — returns `STIGMEM_TOOLS`, a `list[dict]` in OpenAI tool-use
   format.  Pass directly to `chat.completions.create(tools=...)`.

2. **`dispatch(tool_call)`** — executes a tool call returned by the model and
   returns an OpenAI-format `{"role": "tool", ...}` message dict.  Accepts
   both SDK objects (`ChatCompletionMessageToolCall`) and plain dicts.

3. **`run_litellm(model, system_prompt, user_message)`** — thin agentic loop
   via LiteLLM.  Works with any LiteLLM model string: `"ollama/mistral"`,
   `"openai/gpt-4o-mini"`, `"anthropic/claude-3-5-haiku-20241022"`, etc.

4. **`run_openai(model, system_prompt, user_message, base_url, api_key)`** —
   loop via the OpenAI Python SDK.  Set `base_url="http://localhost:11434/v1"`
   to target a local Ollama server.

The adapter depends on `stigmem-node` for plugin discovery metadata and the
Python SDK client surface used by the adapter. `litellm` and `openai` are
optional dependencies needed only for `run_litellm()` and `run_openai()`
respectively.

## Files

| File | Purpose |
|---|---|
| `src/stigmem_plugin_openai_tools/adapter.py` | Adapter - tool declarations + dispatch + LiteLLM/OpenAI loops |
| `src/stigmem_plugin_openai_tools/manifest.py` | Plugin discovery manifest |
| `tests/conftest.py` | pytest path setup |
| `tests/test_openai_tools_adapter.py` | Unit tests (respx-mocked) |

## Installation

### Requirements

- Python ≥ 3.11
- `stigmem-py`: `pip install stigmem-py` (or from workspace)
- Optional - for `run_litellm()`: `pip install 'stigmem-plugin-openai-tools-adapter[litellm]'`
- Optional - for `run_openai()`: `pip install 'stigmem-plugin-openai-tools-adapter[openai]'`
- Optional - local OSS models: [install Ollama](https://ollama.com) + pull a tool-capable model (`ollama pull mistral`)

### Environment variables

```bash
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key                # optional
STIGMEM_SOURCE_ENTITY=agent:my-oss-agent  # entity URI for assertions
```

## Enable

There is no node-global `STIGMEM_*_ENABLED` gate. Installing the package makes
the plugin manifest discoverable through `stigmem.plugins`; a host application
must import and call the adapter explicitly.

```python
from stigmem_plugin_openai_tools import StigmemOpenAIToolsAdapter

adapter = StigmemOpenAIToolsAdapter.from_env()
```

## Disable

Stop importing the adapter in the host application, remove any host-level model
tool configuration that references `STIGMEM_TOOLS`, and uninstall the package
when it is no longer needed.

## Usage

### Raw tool declarations (no LLM SDK needed)

```python
from stigmem_plugin_openai_tools import STIGMEM_TOOLS

# Pass to any OpenAI-compatible endpoint
print(STIGMEM_TOOLS[0]["function"]["name"])  # → "assert_fact"
```

### With LiteLLM — Ollama

```python
from stigmem_plugin_openai_tools import StigmemOpenAIToolsAdapter

adapter = StigmemOpenAIToolsAdapter.from_env()

answer = adapter.run_litellm(
    model="ollama/mistral",
    system_prompt="You are a helpful agent with access to a shared knowledge base.",
    user_message="What role does user:alice have?",
)
print(answer)
```

### With LiteLLM — OpenAI

```python
answer = adapter.run_litellm(
    model="openai/gpt-4o-mini",
    system_prompt="...",
    user_message="...",
)
```

### With OpenAI SDK against a local Ollama server

```python
from stigmem_plugin_openai_tools import StigmemOpenAIToolsAdapter

adapter = StigmemOpenAIToolsAdapter.from_env()

answer = adapter.run_openai(
    model="mistral",
    system_prompt="You are a helpful agent.",
    user_message="Assert that user:alice has role engineer.",
    base_url="http://localhost:11434/v1",
    api_key="ollama",   # Ollama ignores this; SDK requires a non-empty value
)
```

### Manual dispatch loop

```python
import litellm
from stigmem_plugin_openai_tools import StigmemOpenAIToolsAdapter

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

# Continue the loop until no more tool calls...
```

## Test

```bash
cd stigmem
uv run pytest experimental/openai-tools-adapter/tests -q
```

No live node, Ollama, or LiteLLM key required — all HTTP calls are mocked with respx.

## Uninstall

```bash
python -m pip uninstall stigmem-plugin-openai-tools-adapter
```

## Ollama model compatibility

Tool use requires a model that supports function calling.  Tested models:

| Model | Ollama tag | Tool-use support |
|---|---|---|
| Mistral | `mistral` | ✅ |
| Llama 3.1+ | `llama3.1` | ✅ |
| Qwen 2.5 | `qwen2.5` | ✅ |
| Phi-4 | `phi4` | ✅ |

Pull a tool-capable model: `ollama pull mistral`

## Protocol notes

- The OpenAI format uses **lower-case** JSON Schema type strings (`"string"`,
  `"object"`, `"array"`). This is the opposite of Gemini's upper-case format.
- `dispatch()` accepts both SDK model objects and plain dicts, making it easy
  to use from any framework or in tests.
- The `run_litellm()` and `run_openai()` loops cap at `max_rounds=10`.
- Dispatch errors are returned as `{"error": "..."}` in the tool message so
  the model can reason about failures.

## Package Lifecycle

`stigmem-plugin-openai-tools-adapter` is an experimental, opt-in adapter
package for the `v0.9.0a10` adapter publication batch. Installing the package
makes it discoverable through the `stigmem.plugins` entry-point group. The
adapter performs no node-global work unless a host application imports it and
calls its surfaces.
