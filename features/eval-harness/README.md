---
feature_id: eval-harness
title: Evaluation harness
status: deferred
stability: experimental
since: 0.9.0a1
owner: unowned
feature_type: tooling
default_surface: internal
canonical_spec: none
implementation_path: experimental/eval-harness
package: none
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

# Evaluation Harness

The evaluation harness is a deferred tooling concept for validating Stigmem
node correctness, adversarial resilience, and recall quality against a live
node. The current repository surface under `experimental/eval-harness` contains
concept documentation and lifecycle status, not a complete runnable harness.

This feature remains outside the current alpha artifact set until implementation
files, corpus fixtures, CI wiring, live-node validation, and ownership are
complete.

## Current State

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `internal` |
| Primary implementation | `experimental/eval-harness` |
| Primary package | `none` |
| Canonical spec | `none` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
