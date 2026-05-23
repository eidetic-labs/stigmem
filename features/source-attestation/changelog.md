# Source Attestation Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for source-attestation spec, status, evidence, security, and
  feature-local history.
- Validated the default-install boundary: source-attestation environment gates
  alone do not enable assertion validation, recall ranking, or federation
  inbound validation unless the plugin is registered.
- Validated plugin-loaded assertion enforcement for direct source matches,
  normalized source matches, and identity-provided delegated source entities.
- Validated plugin-owned recall and federation behavior, including source-trust
  weight gating and the boundary that inbound federated facts are guarded but
  not locally re-attested.
- Clarified that release artifact provenance, standalone plugin publication,
  API-backed delegation persistence, key-rotation conformance, warn-mode
  persistence, and `attested: true` marking remain outside the current alpha
  validation.

## Post-v0.9.0a1 Main

- Added `experimental/source-attestation/` as the
  `stigmem-plugin-source-attestation` source package.
- Added metadata, configuration gates, and hook handlers for assertion
  validation, recall ranking, and federation inbound validation.
- Kept signed/package artifact evidence deferred to the all-plugins launch
  lane.
