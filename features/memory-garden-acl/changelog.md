# Memory Garden Advanced ACL Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for Memory Garden advanced ACL spec, status, evidence, security, and
  feature-local history.

## Post-v0.9.0a1 Main

- Added `experimental/memory-garden-acl/` as the
  `stigmem-plugin-memory-garden-acl` source package.
- Added plugin registration/order tests and plugin-loaded validation for
  registration gates and explicit opt-in flags.
- Preserved core garden CRUD, membership, and direct `garden_id` guards as core
  behavior outside the plugin.
