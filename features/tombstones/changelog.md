# RTBF Tombstones Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for tombstone spec, status, evidence, security, and feature-local
  history.
- Validated `v0.9.0a5` alpha scope for `stigmem-plugin-tombstones`: default
  installs remain inert unless the plugin is registered and operator gates are
  enabled, tombstone issuance remains admin-only, inbound federation
  tombstones require signer authority and valid signatures, tombstone
  decisions emit audit events, selective revocation restores only the intended
  entity, and legal-hold/no-leak paths are covered across fact, recall, card,
  provenance, and time-travel surfaces.

## Post-v0.9.0a1 Main

- Added `experimental/tombstones/` as the `stigmem-plugin-tombstones` source
  package.
- Added plugin manifest, config schema, hook placeholders, migration
  declaration, registration tests, plugin-loaded tests, and deterministic hook
  ordering coverage.
- Kept signed/package artifact evidence deferred to the plugin launch lane.
