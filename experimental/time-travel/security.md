---
feature: time-travel
spec_id: Spec-X3-Time-Travel-Queries
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-16
owned_risks: []
contributed_risks:
  - R-17
  - R-18
---

# Time-Travel Queries Security

This document is the feature-owned security analysis for
`experimental/time-travel/`. It is registered from the unified threat model at
[`spec/security/threat-model.md`](../../spec/security/threat-model.md).

## Owned Risks

None currently identified. Time-travel queries do not own a standalone R-XX
risk in the v0.9.0a1 threat model. The feature is still security-sensitive
because it contributes to tombstone legal-hold exposure and CID field-exclusion
correctness.

## Contributed Risks

### R-17: Legal-hold historical data exposure

R-17 is canonical in
[`experimental/tombstones/security.md`](../tombstones/security.md). Time-travel
contributes to the risk because `as_of` reads are the mechanism that can expose
pre-tombstone history when a tombstone carries `legal_hold: true`. The
time-travel plugin must preserve the legal-hold access boundary: non-admin
callers cannot retrieve legal-hold history, and every preserved-data read must
leave audit evidence.

### R-18: CID field-exclusion tampering

R-18 remains protocol-level in
[`spec/security/threat-model.md`](../../spec/security/threat-model.md) because
CID semantics are core per ADR-017. Time-travel contributes to the risk because
historical reads depend on `valid_until` and source-trust metadata that are not
the CID identity itself. A federated peer must not be able to extend
`valid_until` or inflate `source_trust` and then make a fact appear valid in an
`as_of` query when local policy would reject that metadata.

## Threat Model Delta

Time-travel adds a historical-read boundary to ordinary fact and recall reads.
The key delta is that visibility is evaluated against a caller-provided
timestamp rather than only the current projection. That makes erased,
expired, or legal-hold data handling part of the security surface.

The plugin must treat `as_of` as an explicit elevated query mode. It must reuse
the same authentication, scope, garden, tombstone, CID, and federation-integrity
checks as current reads, then apply historical visibility after those checks.

## Operator Scenarios

- Keep the time-travel plugin disabled unless historical reads are an explicit
  operator requirement.
- Treat `as_of` access to legal-hold data as a compliance-sensitive admin
  action.
- Review audit trails for legal-hold reads before exporting or sharing
  historical query results.
- Do not accept federated metadata changes that extend `valid_until` beyond
  locally observed values.

## Conformance Pointers

Required adversarial vectors before promotion:

- default installs reject `as_of` queries when the plugin is not loaded;
- non-admin callers cannot retrieve legal-hold history through `as_of`;
- time-travel reads exclude tombstoned data unless the caller is authorized for
  the legal-hold path;
- federation ingest rejects `valid_until` extension before historical reads can
  observe the fact;
- source-trust values used during historical reads are recomputed locally.

## Reintroduction Gates

Gate 1 remains open until legal-hold access controls and R-18 integration tests
cover the time-travel read path. The feature must not graduate while historical
reads can bypass tombstone, CID, or source-trust controls.

## Cross-References

- Unified threat model: [`spec/security/threat-model.md`](../../spec/security/threat-model.md)
- Feature status: [`STATUS.md`](STATUS.md)
- Feature spec: [`spec.md`](spec.md)
- Tombstone security analysis: [`experimental/tombstones/security.md`](../tombstones/security.md)
- ADR-018: [`docs/adr/018-security-documentation-colocation.md`](../../docs/adr/018-security-documentation-colocation.md)
