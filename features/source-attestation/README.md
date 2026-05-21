---
feature_id: source-attestation
title: Source attestation
status: active
stability: experimental
since: 0.9.0a1
owner: maintainers
feature_type: plugin
default_surface: opt-in
canonical_spec: Spec-X6-Source-Attestation
implementation_path: experimental/source-attestation
package: stigmem-plugin-source-attestation
adr_refs:
  - ADR-008
  - ADR-010
  - ADR-011
  - ADR-018
  - ADR-020
security_refs:
  - R-22
release_lines:
  - v0.9.0a1
  - 0.9.xA
---

# Source Attestation

Source attestation binds asserted fact `source` values to authenticated
principals and delegation lists. The feature is implemented as the opt-in
`stigmem-plugin-source-attestation` source package. Default installs remain
inert unless the plugin is registered and the relevant gates are enabled.

## Current State

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| Default surface | `opt-in` |
| Primary implementation | `experimental/source-attestation/` |
| Primary package | `stigmem-plugin-source-attestation` |
| Canonical spec | `Spec-X6-Source-Attestation` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
