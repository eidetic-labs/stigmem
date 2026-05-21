---
feature_id: cognee-adapter
title: Cognee adapter
status: deferred
stability: experimental
since: 0.9.0a1
owner: unowned
feature_type: adapter
default_surface: external
canonical_spec: none
implementation_path: experimental/cognee-adapter
package: stigmem-cognee-adapter
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

# Cognee Adapter

The Cognee adapter bridges Stigmem atomic facts with Cognee's knowledge-graph
layer. It serializes facts into structured text for Cognee ingestion and maps
Cognee semantic-search results back into Stigmem-shaped fact records.

The adapter source exists under `experimental/cognee-adapter`. It is preserved
as source-only design-partner surface area and remains outside the current
alpha artifact set until ownership, package validation, dependency validation,
and live Cognee integration evidence are complete.

## Current State

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Primary implementation | `experimental/cognee-adapter` |
| Primary package | `stigmem-cognee-adapter` |
| Canonical spec | `none` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
