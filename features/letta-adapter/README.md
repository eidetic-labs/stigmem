---
feature_id: letta-adapter
title: Letta adapter
status: deferred
stability: experimental
since: 0.9.0a1
owner: unowned
feature_type: adapter
default_surface: external
canonical_spec: none
implementation_path: experimental/letta-adapter
package: stigmem-letta-adapter
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

# Letta Adapter

The Letta adapter bridges Stigmem shared coordination facts with Letta
per-agent archival memory. It writes Stigmem facts into a Letta agent as tagged
archival passages and can read Letta archival memory back as Stigmem-shaped
records.

The adapter source exists under `experimental/letta-adapter`. It is preserved
as source-only design-partner surface area and remains outside the current
alpha artifact set until ownership, package validation, dependency validation,
and live Letta integration evidence are complete.

## Current State

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Primary implementation | `experimental/letta-adapter` |
| Primary package | `stigmem-letta-adapter` |
| Canonical spec | `none` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
