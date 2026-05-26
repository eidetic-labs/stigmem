---
title: OpenAI Tools Adapter
sidebar_label: OpenAI Tools Adapter
description: Experimental OpenAI-compatible tool-use adapter package.
audience: Operator
---

# OpenAI Tools Adapter

Package: `stigmem-plugin-openai-tools-adapter`

The OpenAI Tools adapter exposes Stigmem client operations as
OpenAI-compatible function-calling declarations and tool-result messages. It is
intended for host applications that use LiteLLM, the OpenAI Python SDK, or
OpenAI-compatible local endpoints such as Ollama.

## Install

```bash
python -m pip install 'stigmem-plugin-openai-tools-adapter>=0.1.0,<2.0.0'
```

Optional provider loops are extra-scoped:

```bash
python -m pip install 'stigmem-plugin-openai-tools-adapter[litellm]>=0.1.0,<2.0.0'
python -m pip install 'stigmem-plugin-openai-tools-adapter[openai]>=0.1.0,<2.0.0'
```

The package is also available through the meta-package extra:

```bash
python -m pip install --pre 'stigmem[openai-tools-adapter]'
```

## Enablement

There is no node-global `STIGMEM_*_ENABLED` gate. Installing the package makes
the adapter discoverable through `stigmem.plugins`; a host application must
import and call the adapter explicitly.

Required runtime configuration for `from_env()`:

```bash
export STIGMEM_URL=http://localhost:8765
export STIGMEM_API_KEY=sk-your-key
export STIGMEM_SOURCE_ENTITY=agent:openai-tools
```

## Surfaces

| Surface | Behavior |
| --- | --- |
| `STIGMEM_TOOLS` | Static OpenAI-format tool declaration list. |
| `tools()` | Returns `STIGMEM_TOOLS` for direct chat-completion API use. |
| `dispatch(tool_call)` | Executes one model-returned tool call and returns an OpenAI-format tool message. |
| `run_litellm()` | Runs a bounded LiteLLM tool loop. |
| `run_openai()` | Runs a bounded OpenAI SDK tool loop against hosted or OpenAI-compatible local endpoints. |

## Validation Boundary

Mocked adapter tests, package metadata, discovery manifest, security notes, and
feature records are complete for v0.1.0. Live LiteLLM, OpenAI SDK, and Ollama
validation remains operator-owned for deployment.

Feature record: [`features/openai-tools-adapter`](https://github.com/eidetic-labs/stigmem/tree/main/features/openai-tools-adapter).
