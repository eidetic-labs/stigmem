# Source Attestation Security

## Owned Risks

None currently identified. Source attestation does not own a standalone R-XX
risk in the current threat model.

## Contributed Risks

### R-22: Release supply-chain integrity

Source attestation contributes to R-22 because operators must trust both the
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
does not prove release artifact provenance.

Federation inbound validation is a guard on peer/source consistency. It does
not transform an inbound federated fact into a locally attested assertion, and
it does not replace the core federation source-ownership checks that already
run before plugin hook dispatch on peer and capability-token push paths.

## Conformance Pointers

Required adversarial vectors before promotion:

- a caller cannot assert a `source` URI that is not bound to its authenticated
  principal;
- warn-mode persistence is explicitly dispositioned before graduation;
- enforce mode rejects mismatched source claims;
- key rotation invalidates old source-binding material according to policy;
- source-attested facts survive federation without allowing peers to forge
  local source identity or be silently re-attested as local facts.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
