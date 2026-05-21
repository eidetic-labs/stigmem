---
spec_id: Spec-X6-Source-Attestation
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-21
supersedes: pre-reset section 18 source-attestation material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-09-Audit-Log >= 0.1.0-alpha.0
---

# Spec-X6-Source-Attestation

## Motivation

Without source attestation, the `source` field in a fact request is
caller-declared. An authenticated principal can claim another entity as the
source of a fact, which undermines audit trails, trust scoring, and future
keypair-signed attribution.

## Attestation Model

When auth is enabled, the node resolves the caller's registered `entity_uri`
and `allowed_source_entities`, normalizes source URIs, and checks that the
fact's `source` is authorized by the caller.

Modes:

- `enforce`: reject unauthorized source claims.
- `warn`: accept but record `attested: false`.
- `off`: do not check source claims.

Default installs do not run this behavior. Runtime enforcement requires
`stigmem-plugin-source-attestation` plus explicit plugin gates.

## Key Registration

Source attestation depends on binding `entity_uri` and optional delegation
lists to API keys at creation time. The `entity_uri` binding is immutable; a
caller must revoke and recreate a key to change source identity.

## Integration Points

The plugin owns:

- assertion validation before fact writes;
- recall ranking signals that can prefer attested facts;
- federation inbound validation so peers cannot forge local source identity.

## Non-Goals

- Source attestation does not prove that the plugin package or node binary came
  from a signed release.
- Release artifact provenance remains tracked by R-22.
- This feature does not graduate source attestation into the default install.
