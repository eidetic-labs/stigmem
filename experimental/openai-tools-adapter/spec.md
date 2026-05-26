---
spec_id: Spec-X7-OpenAI-Tools-Adapter
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0a10 plugin package
last_updated: 2026-05-26
supersedes: features/openai-tools-adapter/spec.md package projection
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
title: OpenAI Tools Adapter
sidebar_label: OpenAI Tools Adapter
audience: Spec
description: "Package projection for OpenAI-compatible tool-use adapter semantics."
stability: experimental
since: 0.9.0a10
---

# OpenAI Tools Adapter Spec

## Scope

The OpenAI-compatible tools adapter maps Stigmem client operations into
OpenAI-style `tools` declarations and tool-result messages. It does not define
OpenAI, LiteLLM, Ollama, or Stigmem node API semantics.

This package covers:

- the `stigmem-plugin-openai-tools-adapter` package under
  `experimental/openai-tools-adapter`;
- plugin discovery through the `stigmem.plugins` entry-point group;
- static OpenAI-format declarations for five Stigmem tool calls;
- dispatch of dict or SDK-object tool calls into Stigmem client operations;
- bounded convenience loops for LiteLLM and the OpenAI Python SDK;
- environment-based Stigmem URL, API key, and source entity configuration.

## Adapter Contract

| Surface | Behavior |
| --- | --- |
| `STIGMEM_TOOLS` | Static OpenAI-format tool declaration list. |
| `tools()` | Returns `STIGMEM_TOOLS` for direct API use. |
| `dispatch(tool_call)` | Executes one model-returned tool call and returns an OpenAI-format tool message. |
| `run_litellm(model, system_prompt, user_message)` | Runs a bounded LiteLLM tool loop using adapter declarations and dispatch. |
| `run_openai(model, system_prompt, user_message, base_url, api_key)` | Runs a bounded OpenAI SDK tool loop, including OpenAI-compatible local endpoints. |
| `plugin_manifest()` | Returns the discovery manifest for `stigmem-plugin-openai-tools-adapter` v0.1.0. |

## Tool Declarations

| Tool | Backing client operation |
| --- | --- |
| `assert_fact` | `StigmemClient.assert_fact()` |
| `query_facts` | `StigmemClient.query()` |
| `resolve_contradiction` | `StigmemClient.resolve_conflict()` |
| `subscribe_scope` | `StigmemClient.query()` scoped to a subscription-style request |
| `lint_scope` | `StigmemClient.lint()` |

## Configuration

| Setting | Purpose |
| --- | --- |
| `STIGMEM_URL` | Required by `from_env()`; points at the Stigmem API. |
| `STIGMEM_API_KEY` | Optional API key passed to `StigmemClient`. |
| `STIGMEM_SOURCE_ENTITY` | Optional source entity; defaults to `agent:openai-tools`. |
| `max_rounds` | Tool-loop bound for LiteLLM and OpenAI SDK helpers; defaults to `10`. |

## Non-Goals

- MCP transport or protocol negotiation.
- Provider-specific model certification.
- Making LiteLLM, OpenAI, or Ollama required dependencies for default Stigmem
  installs.
- Maintaining a second Ollama/LiteLLM implementation separate from this
  OpenAI-compatible adapter.

## Canonical Spec Assignment

The canonical feature spec assignment is `Spec-X7-OpenAI-Tools-Adapter`. The
adapter is an external integration spec around existing Stigmem fact/query
behavior, not a new core protocol module.
