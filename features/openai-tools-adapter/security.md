# OpenAI Tools Adapter Security

The OpenAI tools adapter exposes Stigmem write, query, conflict-resolution,
subscription-style query, and lint operations to model tool calls. Its security
posture depends on caller-scoped Stigmem credentials, bounded tool loops, and
operator-controlled model/provider selection.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Credential handling | Stigmem credentials are supplied by environment or constructor arguments, not committed source. | `experimental/openai-tools-adapter/README.md`; `experimental/openai-tools-adapter/src/stigmem_plugin_openai_tools/adapter.py` |
| Tool-loop bounds | `run_litellm()` and `run_openai()` cap loops with `max_rounds`, defaulting to `10`. | `experimental/openai-tools-adapter/src/stigmem_plugin_openai_tools/adapter.py` |
| Dispatch failures | Stigmem and unexpected dispatch failures return JSON error payloads in tool messages. | `experimental/openai-tools-adapter/src/stigmem_plugin_openai_tools/adapter.py`; `experimental/openai-tools-adapter/tests/test_openai_tools_adapter.py` |
| Provider exposure | Operators select LiteLLM model strings or OpenAI-compatible base URLs explicitly. | `experimental/openai-tools-adapter/README.md` |
| Schema compatibility | Tool declarations use lower-case JSON Schema types expected by OpenAI-compatible APIs. | `experimental/openai-tools-adapter/tests/test_openai_tools_adapter.py` |

## Security References

No dedicated R-* audit item is assigned to this adapter. The adapter inherits
the general model-tooling risks of exposing Stigmem write and query operations
to external model runtimes.

## Advisories and Findings

None currently recorded for the adapter.

## Residual Risk

- Hosted model providers may receive prompt, tool-call, and tool-result context
  depending on operator configuration.
- Model-driven calls can write or resolve memory according to the Stigmem
  credentials supplied to the adapter.
- Live provider behavior is operator-owned for v0.1.0 and is not a package
  publication blocker.

## Operator Guidance

- Use least-privilege Stigmem credentials for model agents.
- Prefer local or controlled model endpoints when prompt and memory context
  must stay inside an operator boundary.
- Treat live provider validation as a deployment gate before promoting this
  adapter in an operator environment.
