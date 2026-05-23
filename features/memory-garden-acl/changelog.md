# Memory Garden Advanced ACL Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for Memory Garden advanced ACL spec, status, evidence, security, and
  feature-local history.
- Validated the `v0.9.0a6` Memory Garden advanced ACL alpha horizon: basic
  garden CRUD, membership, direct `garden_id` guards, and quarantine
  moderation remain core; advanced cross-surface behavior remains opt-in behind
  `stigmem-plugin-memory-garden-acl` registration and operator gates.
- Recorded cross-surface disposition for assertion authorization, fact query
  filtering, recall ranking, graph traversal, OIDC permission ceilings,
  subscription delivery/replay, quarantine moderation, and R-21 residual risk.

## Post-v0.9.0a1 Main

- Added `experimental/memory-garden-acl/` as the
  `stigmem-plugin-memory-garden-acl` source package.
- Added plugin registration/order tests and plugin-loaded validation for
  registration gates and explicit opt-in flags.
- Preserved core garden CRUD, membership, and direct `garden_id` guards as core
  behavior outside the plugin.
