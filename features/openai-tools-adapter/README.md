---
feature_id: openai-tools-adapter
title: OpenAI tools adapter
status: deferred
stability: experimental
since: 0.9.0a1
owner: unowned
feature_type: adapter
default_surface: external
canonical_spec: none
implementation_path: experimental/openai-tools-adapter
package: stigmem-openai-tools-adapter
adr_refs:
  - ADR-002
  - ADR-009
  - ADR-020
security_refs:
  - none
release_lines:
  - v0.9.0a1
  - 0.9.xA
---

# OpenAI Tools Adapter

The OpenAI tools adapter exposes Stigmem operations in OpenAI-compatible
function-calling format. It provides lower-case JSON Schema tool declarations,
dispatch for model-returned tool calls, and optional convenience loops for
LiteLLM and the OpenAI Python SDK.

The adapter is preserved as experimental external adapter surface area under
`experimental/openai-tools-adapter`. It remains outside the current alpha
artifact set until ownership, dependency validation, package validation, and
live model validation are complete.

## Current State

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Primary implementation | `experimental/openai-tools-adapter` |
| Primary package | `stigmem-openai-tools-adapter` |
| Canonical spec | `none` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
