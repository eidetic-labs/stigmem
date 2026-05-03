# Stigmem — Gemini Adapter

Integrates Stigmem with the [Google Gemini API](https://ai.google.dev) using
Gemini's native **FunctionDeclaration** format.

## Design

The adapter has three surfaces:

1. **`gemini_tools()`** — returns `STIGMEM_FUNCTION_DECLARATIONS`, a
   `list[dict]` of Google `FunctionDeclaration`-shaped JSON objects ready to
   pass to `genai.protos.FunctionDeclaration(**t)` or directly to the REST API.

2. **`dispatch(fn_name, fn_args)`** — executes a Stigmem tool call triggered
   by a Gemini `FunctionCall` part and returns a JSON string to wrap in a
   `FunctionResponse`.

3. **`run(system_prompt, user_message)`** — a thin agentic loop that handles
   the full tool-use turn sequence. Requires `google-generativeai` installed.

The adapter depends only on `stigmem-py`. The `google-generativeai` SDK is an
optional dependency needed only for `run()`.

## Files

| File | Purpose |
|---|---|
| `adapter.py` | Adapter — function declarations + dispatch + agentic loop |
| `tests/conftest.py` | pytest path setup |
| `tests/test_adapter.py` | Unit tests (respx-mocked) |

## Setup

### Requirements

- Python ≥ 3.11
- `stigmem-py`: `pip install stigmem-py` (or from workspace)
- Optional — for `run()`: `pip install google-generativeai`

### Environment variables

```bash
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key          # optional
STIGMEM_SOURCE_ENTITY=agent:gemini   # entity URI for this agent
STIGMEM_GEMINI_MODEL=gemini-2.0-flash  # model to use in run()
GOOGLE_API_KEY=your-gemini-key       # required for run()
```

## Usage

### Raw declarations (no Gemini SDK needed)

```python
from adapter import STIGMEM_FUNCTION_DECLARATIONS

# Pass to any Gemini-compatible API as plain JSON
print(STIGMEM_FUNCTION_DECLARATIONS[0]["name"])  # → "assert_fact"
```

### With the Gemini SDK

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

# Dispatch tool calls
for part in response.candidates[0].content.parts:
    if part.function_call:
        result_json = adapter.dispatch(part.function_call.name, dict(part.function_call.args))
        # wrap result_json in a FunctionResponse and continue the loop
```

### Agentic loop (convenience)

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

## Running tests

```bash
cd stigmem
uv run pytest adapters/gemini/tests/ -v
```

No live node or Gemini API key required — all HTTP calls are mocked with respx.

## Protocol notes

- Gemini uses `"OBJECT"`, `"STRING"`, `"NUMBER"`, `"BOOLEAN"`, `"INTEGER"`,
  `"ARRAY"` as type strings (upper-case). This differs from JSON Schema / OpenAI
  which use lower-case.
- The `run()` loop caps at `max_rounds=10` to prevent infinite tool-call cycles.
- Tool dispatch errors are caught and returned as `{"error": "..."}` JSON so the
  model can reason about failures rather than crashing the loop.
