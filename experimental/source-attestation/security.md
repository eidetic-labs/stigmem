---
feature: source-attestation
spec_id: Spec-X6-Source-Attestation
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-16
owned_risks: []
contributed_risks:
  - R-22
---

# Source Attestation Security

This document is the feature-owned security analysis for
`experimental/source-attestation/`. It is registered from the unified threat
model at [`spec/security/threat-model.md`](../../spec/security/threat-model.md).

## Owned Risks

None currently identified. Source attestation does not own a standalone R-XX
risk in the v0.9.0a1 threat model. It remains a security feature because it
binds fact authorship to authenticated principals and will eventually depend on
release-artifact provenance.

## Contributed Risks

### R-22: Release supply-chain integrity

R-22 remains protocol-level in
[`spec/security/threat-model.md`](../../spec/security/threat-model.md). Source
attestation contributes to the risk because operators need to trust both the
attestation code they run and the released artifacts that delivered it. Until
signed release artifacts, SBOMs, and Rekor entries exist for release builds,
source-attestation deployment guidance must avoid implying end-to-end supply
chain assurance.

## Threat Model Delta

Source attestation adds a caller-to-source binding boundary. Without it, an
authenticated caller can claim an arbitrary `source` URI on asserted facts. With
it, the node verifies that the asserted source is authorized by the caller's
registered key material and configured attestation policy.

The feature narrows spoofing and repudiation risk for fact authorship, but it
does not prove that a plugin package or node binary came from a signed release.
That distinction keeps release supply-chain integrity in R-22.

## Operator Scenarios

- Enable source attestation for multi-tenant or public-write nodes before
  accepting facts from independently administered callers.
- Treat unattested facts as lower-trust data unless a single-operator
  deployment intentionally accepts that mode.
- Rotate attestation keys when a caller key is revoked or suspected
  compromised.
- Do not describe source-attestation as release signing; release signing is
  tracked separately by R-22.

## Conformance Pointers

Required adversarial vectors before promotion:

- a caller cannot assert a `source` URI that is not bound to its authenticated
  principal;
- warn mode records unattested facts without silently marking them trusted;
- enforce mode rejects mismatched source claims;
- key rotation invalidates old source-binding material according to policy;
- source-attested facts survive federation without allowing peers to forge
  local source identity.

## Reintroduction Gates

Gate 1 remains open until source-binding semantics, warning/enforcement modes,
and key-rotation behavior have conformance coverage. Graduation must also avoid
overstating R-22 until release artifacts are signed and independently
verifiable.

## Cross-References

- Unified threat model: [`spec/security/threat-model.md`](../../spec/security/threat-model.md)
- Feature status: [`STATUS.md`](STATUS.md)
- Feature spec: [`spec.md`](spec.md)
- Source-attestation operator docs: [`docs/docs/security/authentication.md`](../../docs/docs/security/authentication.md)
- ADR-018: [`docs/adr/018-security-documentation-colocation.md`](../../docs/adr/018-security-documentation-colocation.md)
