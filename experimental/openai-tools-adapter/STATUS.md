# OpenAI Tools Adapter Status

**Status:** active experimental adapter package
**Package:** `stigmem-plugin-openai-tools-adapter`
**Version:** `0.1.0`
**Default surface:** opt-in
**Release line:** `v0.9.0a10`

The OpenAI-compatible tools adapter is packaged as an opt-in bridge between
Stigmem client operations and OpenAI-style function-calling/tool-result
messages. It is discoverable through the `stigmem.plugins` entry-point group
after installation, but it has no node-global behavior gate and performs no
work unless a host application imports and calls the adapter.

## Gate Tracking

| Gate | Status | Evidence |
| --- | --- | --- |
| Source layout | Complete | `src/stigmem_plugin_openai_tools/adapter.py`; `src/stigmem_plugin_openai_tools/manifest.py` |
| Package metadata | Complete | `pyproject.toml`; `uv build experimental/openai-tools-adapter` |
| Unit tests | Complete | `tests/test_openai_tools_adapter.py` |
| Security review | Complete for mocked/package scope | `security.md`; `features/openai-tools-adapter/security.md` |
| Live provider validation | Operator-owned | LiteLLM, OpenAI SDK, and Ollama validation are outside v0.1.0 package publication. |

## Publication Scope

Included:

- src-layout Python package metadata;
- plugin discovery manifest;
- mocked adapter tests;
- feature-owned spec, status, evidence, security, and changelog updates;
- public plugin catalog and compatibility projections.

Not included:

- live LiteLLM, OpenAI SDK, or local Ollama acceptance evidence;
- provider credential management beyond documented caller ownership;
- model-specific safety, prompt-injection, or tool-use certification.
