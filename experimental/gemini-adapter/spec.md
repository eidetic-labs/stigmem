---
spec_id: Spec-X7-Gemini-Adapter
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0a10 plugin package
last_updated: 2026-05-26
supersedes: features/gemini-adapter/spec.md package projection
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-03-HTTP-API >= 0.1.0-alpha.0
title: Gemini Adapter
sidebar_label: Gemini Adapter
audience: Spec
description: "Package projection for Gemini adapter semantics."
stability: experimental
since: 0.9.0a10
---

# Gemini Adapter Spec

## Purpose

`stigmem-plugin-gemini-adapter` maps Stigmem tool operations into
Gemini-native `FunctionDeclaration` dictionaries. It gives host applications a
small bridge for presenting Stigmem fact, query, contradiction, subscription,
and lint operations to Gemini tool-calling flows.

The adapter is intentionally a bridge package, not a node-wide behavior plugin.
Installing it makes the `gemini-adapter` manifest discoverable. Runtime calls
remain explicit through `StigmemGeminiAdapter`.

## Tool Declaration Semantics

`STIGMEM_FUNCTION_DECLARATIONS` contains the five supported Stigmem tools:

- `assert_fact`
- `query_facts`
- `resolve_contradiction`
- `subscribe_scope`
- `lint_scope`

Gemini function declarations use upper-case type strings such as `OBJECT`,
`STRING`, `NUMBER`, `BOOLEAN`, `INTEGER`, and `ARRAY`. The adapter keeps that
shape separate from OpenAI-style lower-case JSON Schema declarations.

## Dispatch Semantics

`dispatch(fn_name, fn_args)` executes the named Stigmem operation against a
configured `StigmemClient` and returns a JSON string suitable for a Gemini
`FunctionResponse`. Dispatch errors are returned as JSON error payloads so the
model loop can continue without an unhandled exception.

## Configuration Surface

The adapter reads these environment variables through
`StigmemGeminiAdapter.from_env()`:

| Variable | Purpose |
| --- | --- |
| `STIGMEM_URL` | Stigmem node URL. |
| `STIGMEM_API_KEY` | Optional Stigmem API key. |
| `STIGMEM_SOURCE_ENTITY` | Source entity URI, defaulting to `agent:gemini`. |
| `STIGMEM_GEMINI_MODEL` | Gemini model name, defaulting to `gemini-2.0-flash`. |
| `GOOGLE_API_KEY` | Gemini API key required for the optional `run()` loop. |

## API

`StigmemGeminiAdapter.from_env()` constructs an adapter from environment.

`gemini_tools()` returns the declaration dictionaries.

`dispatch(fn_name, fn_args)` executes one tool call and returns JSON.

`run(system_prompt, user_message)` runs a bounded Gemini tool-use loop when
`google-generativeai` is installed and configured.

## Failure Modes

- Missing `google-generativeai` raises `ImportError` with an install hint when
  `run()` is called.
- Stigmem HTTP errors become JSON error payloads in `dispatch()`.
- The `run()` loop caps tool-call rounds to avoid infinite model/tool cycles.
- Host applications own user-facing error redaction and retry behavior.
