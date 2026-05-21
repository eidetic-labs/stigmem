---
feature_id: gemini-adapter
title: Gemini adapter
status: deferred
stability: experimental
since: 0.9.0a1
owner: unowned
feature_type: adapter
default_surface: external
canonical_spec: none
implementation_path: experimental/gemini-adapter
package: stigmem-gemini-adapter
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

# Gemini Adapter

The Gemini adapter exposes Stigmem tool calls in Google Gemini's native
`FunctionDeclaration` format. It provides raw function declarations, a dispatch
surface for Gemini function-call parts, and an optional convenience loop for a
tool-enabled Gemini turn.

The adapter source exists under `experimental/gemini-adapter`. It is preserved
as source-only model/tooling adapter surface area and remains outside the
current alpha artifact set until ownership, package validation, dependency
validation, and live Gemini validation are complete.

## Current State

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Primary implementation | `experimental/gemini-adapter` |
| Primary package | `stigmem-gemini-adapter` |
| Canonical spec | `none` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
