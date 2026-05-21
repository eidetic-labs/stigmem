---
feature_id: zep-adapter
title: Zep adapter
status: deferred
stability: experimental
since: 0.9.0a1
owner: unowned
feature_type: adapter
default_surface: external
canonical_spec: none
implementation_path: experimental/zep-adapter
package: stigmem-zep-adapter
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

# Zep Adapter

The Zep adapter bridges Stigmem shared coordination facts with Zep
per-user/per-session episodic memory. It mirrors Stigmem facts into a Zep
session as structured system messages and maps Zep extracted facts back into
Stigmem-shaped records for query hydration or re-assertion.

The adapter source exists under `experimental/zep-adapter`. It is preserved as
source-only design-partner surface area and remains outside the current alpha
artifact set until ownership, package validation, dependency validation, and
live Zep integration evidence are complete.

## Current State

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Primary implementation | `experimental/zep-adapter` |
| Primary package | `stigmem-zep-adapter` |
| Canonical spec | `none` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
