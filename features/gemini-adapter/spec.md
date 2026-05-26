# Gemini Adapter Spec

## Scope

The Gemini adapter maps Stigmem tool operations into Gemini-native function
declarations and dispatch behavior. It does not define Gemini API behavior or
Stigmem node API semantics.

This feature covers:

- the `stigmem-plugin-gemini-adapter` source package under
  `experimental/gemini-adapter`;
- `STIGMEM_FUNCTION_DECLARATIONS` in Gemini `FunctionDeclaration`-shaped JSON;
- `gemini_tools()` for returning those declarations;
- `dispatch(fn_name, fn_args)` for executing Gemini function calls against a
  configured Stigmem client;
- optional `run(system_prompt, user_message)` convenience loop using
  `google-generativeai`;
- environment-based Stigmem URL, API key, source entity, and Gemini model
  configuration.

## Adapter Contract

| Surface | Behavior |
| --- | --- |
| `gemini_tools()` | Returns Gemini-compatible function declaration dictionaries. |
| `dispatch(fn_name, fn_args)` | Executes the named Stigmem tool and returns a JSON string suitable for a Gemini `FunctionResponse`. |
| `run(system_prompt, user_message)` | Runs a bounded Gemini tool-use loop when `google-generativeai` is installed and configured. |
| Dispatch errors | Return JSON error payloads instead of raising through the model loop. |

## Configuration

| Setting | Purpose |
| --- | --- |
| `STIGMEM_URL` | Stigmem node URL. |
| `STIGMEM_API_KEY` | Optional Stigmem API key. |
| `STIGMEM_SOURCE_ENTITY` | Source entity URI, defaulting to `agent:gemini`. |
| `STIGMEM_GEMINI_MODEL` | Gemini model name, defaulting to `gemini-2.0-flash`. |
| `GOOGLE_API_KEY` | Gemini API key required for the optional `run()` loop. |

## Function Declaration Contract

Gemini function declarations use upper-case type strings such as `OBJECT`,
`STRING`, `NUMBER`, `BOOLEAN`, `INTEGER`, and `ARRAY`. The adapter keeps that
shape separate from OpenAI-style lower-case JSON Schema declarations.

## Non-Goals

- Defining stable Gemini SDK package compatibility beyond the v0.1.0 optional
  runtime extra.
- Running an MCP server.
- Making Gemini required for Stigmem node availability.
- Defining new Stigmem protocol semantics.

## Canonical Spec Assignment

`Spec-X7-Gemini-Adapter` is the package projection for this external adapter.
It remains an adapter around existing Stigmem tool and client behavior, not a
standalone Stigmem protocol module.
