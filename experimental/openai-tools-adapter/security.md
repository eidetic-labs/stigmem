---
feature: openai-tools-adapter
spec_id: Spec-X7-OpenAI-Tools-Adapter
status: Experimental
applies_to: stigmem v0.9.0a10
last_updated: 2026-05-26
owned_risks: []
contributed_risks:
  - R-01
  - R-02
  - R-21
---

# OpenAI Tools Adapter Security Review

The OpenAI-compatible tools adapter exposes Stigmem write, query,
conflict-resolution, subscription-style query, and lint operations to model
tool calls. Its security posture depends on caller-scoped Stigmem credentials,
bounded tool loops, and operator-controlled model/provider selection.

This adapter contributes to existing feature-security risks R-01, R-02, and
R-21 because host applications can route scoped fact content to external model
providers, then authorize model-returned tool calls to read, write, lint, or
resolve Stigmem facts.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Credential handling | Stigmem credentials are supplied by environment or constructor arguments, not committed source. | `README.md`; `src/stigmem_plugin_openai_tools/adapter.py` |
| Tool-loop bounds | `run_litellm()` and `run_openai()` cap loops with `max_rounds`, defaulting to `10`. | `src/stigmem_plugin_openai_tools/adapter.py` |
| Dispatch failures | Stigmem and unexpected dispatch failures return JSON error payloads in tool messages. | `src/stigmem_plugin_openai_tools/adapter.py`; `tests/test_openai_tools_adapter.py` |
| Provider exposure | Operators select LiteLLM model strings or OpenAI-compatible base URLs explicitly. | `README.md` |
| Schema compatibility | Tool declarations use lower-case JSON Schema types expected by OpenAI-compatible APIs. | `tests/test_openai_tools_adapter.py` |

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
