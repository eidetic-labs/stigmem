# RTBF Tombstones Security

## Owned Risks

### R-16: Tombstone denial of service

An attacker with a compromised admin key can issue tombstones for important
entity URIs and suppress facts that agents or operators depend on. Tombstones
are deliberately strong because they support erasure workflows; that same
strength gives a malicious admin credential a high blast radius.

Current controls are admin-only issuance, admin audit events, API-key max-age,
and tombstone audit trail requirements. Required mitigation is an operator and
protocol workflow for high-blast-radius tombstones: second-admin approval for
sensitive entities, explicit revocation runbooks, and tests that prove
tombstone revocation restores only the intended read surface.

### R-17: Legal-hold historical data exposure

A tombstone with `legal_hold: true` suppresses normal reads but intentionally
preserves historical facts for lawful preservation. If an admin key is later
compromised, an attacker may be able to retrieve pre-tombstone history via
`as_of` time-travel queries.

Required mitigation is a narrower legal-hold access model, such as a distinct
`legal_hold_reader` capability, plus integration tests proving non-admin keys
cannot retrieve legal-hold history across a tombstone boundary.

## Threat Model Delta

Tombstones add admin issuance, revocation, and legal-hold read paths to the
existing admin trust boundary. The main change is that an admin action can
suppress or preserve historical fact visibility across ordinary reads,
time-travel reads, and federation propagation.

## Conformance Pointers

Required adversarial vectors before promotion:

- tombstone issued by a non-admin key returns 403;
- forged tombstone signatures are rejected;
- non-admin `as_of` reads cannot cross a legal-hold tombstone boundary;
- tombstone revocation restores the intended entity only;
- federation inbound tombstones without tombstone authority are rejected.

## Residual Risk

Gate 1 remains open. The feature cannot graduate until tombstone DoS recovery,
legal-hold access separation, and federation authority checks have complete
design and evidence.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
