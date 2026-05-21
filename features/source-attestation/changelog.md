# Source Attestation Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for source-attestation spec, status, evidence, security, and
  feature-local history.

## Post-v0.9.0a1 Main

- Added `experimental/source-attestation/` as the
  `stigmem-plugin-source-attestation` source package.
- Added metadata, configuration gates, and hook handlers for assertion
  validation, recall ranking, and federation inbound validation.
- Kept signed/package artifact evidence deferred to the all-plugins launch
  lane.
