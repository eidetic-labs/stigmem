---
feature: tombstones
spec_id: Spec-X2-RTBF-Tombstones
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-15
owned_risks:
  - R-16
  - R-17
contributed_risks: []
---

# RTBF Tombstones Security

This document is the feature-owned security analysis for
`experimental/tombstones/`. It is registered from the unified threat model at
[`spec/security/threat-model.md`](../../spec/security/threat-model.md).

## Owned Risks

### R-16: Tombstone denial of service

**Threat refs:** T7-D2  
**STRIDE class:** Denial of service  
**Status:** Open  
**Likelihood:** Low  
**Impact:** High  
**Priority:** Medium  
**Spec refs:** `Spec-X2-RTBF-Tombstones`, §23.2

An attacker with a compromised admin key can issue tombstones for important
entity URIs and suppress facts that agents or operators depend on. Tombstones
are deliberately strong because they support erasure workflows; that same
strength gives a malicious admin credential a high blast radius.

Current controls are admin-only issuance, admin audit events, API-key max-age,
and tombstone audit trail requirements. These controls help detection and
response but do not prevent an authenticated admin from issuing damaging
tombstones.

Required mitigation is an operator and protocol workflow for high-blast-radius
tombstones: second-admin approval for sensitive entities, explicit revocation
runbooks, and tests that prove tombstone revocation restores only the intended
read surface.

### R-17: Legal-hold historical data exposure

**Threat refs:** T7-I1  
**STRIDE class:** Information disclosure  
**Status:** Open  
**Likelihood:** Low  
**Impact:** High  
**Priority:** Medium  
**Spec refs:** `Spec-X2-RTBF-Tombstones`, §24.3.2

A tombstone with `legal_hold: true` suppresses normal reads but intentionally
preserves historical facts for lawful preservation. If an admin key is later
compromised, an attacker may be able to retrieve pre-tombstone history via
`as_of` time-travel queries. That exposure conflicts with an RTBF data
subject's expectation that erased data is no longer reachable.

Current controls restrict legal-hold `as_of` responses to admin keys and
require audit events for legal-hold issuance. The residual risk is that a
single compromised admin key may still expose preserved history.

Required mitigation is a narrower legal-hold access model, such as a distinct
`legal_hold_reader` capability, plus integration tests proving non-admin keys
cannot retrieve legal-hold history across a tombstone boundary.

## Contributed Risks

None currently identified. Tombstones interact with R-18, but CID integrity is
core per ADR-017 and remains canonical in the protocol-level threat model.

## Threat Model Delta

Tombstones add admin issuance, revocation, and legal-hold read paths to the
existing admin trust boundary. The main change is that an admin action can
suppress or preserve historical fact visibility for an entity across ordinary
reads, time-travel reads, and federation propagation.

## Operator Scenarios

- Treat tombstone issuance as a compliance-impacting administrative action.
- Rotate admin keys immediately if unauthorized tombstone issuance is
  suspected.
- During legal hold, review who can perform `as_of` queries and keep a separate
  audit trail for every preserved-data access.

## Conformance Pointers

Required adversarial vectors before promotion:

- tombstone issued by a non-admin key returns 403;
- forged tombstone signatures are rejected;
- non-admin `as_of` reads cannot cross a legal-hold tombstone boundary;
- tombstone revocation restores the intended entity only;
- federation inbound tombstones without tombstone authority are rejected.

## Reintroduction Gates

Gate 1 remains open. The threat-model delta must decide whether tombstones
need a dedicated capability tier, two-admin sign-off for sensitive entities,
and narrower legal-hold reader permissions before the feature can graduate.

## Cross-References

- Unified threat model: [`spec/security/threat-model.md`](../../spec/security/threat-model.md)
- Feature status: [`STATUS.md`](STATUS.md)
- Feature spec: [`spec.md`](spec.md)
- Security scenarios: [`docs/docs/security/scenarios.md`](../../docs/docs/security/scenarios.md)
- ADR-018: [`docs/adr/018-security-documentation-colocation.md`](../../docs/adr/018-security-documentation-colocation.md)
