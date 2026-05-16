# PR 4e Memory Garden Advanced ACL Extraction Analysis

Issue: #331
Parent: #329
Date: 2026-05-16

## Summary

PR 4e should extract Memory Garden **advanced ACL** behavior into
`stigmem-plugin-memory-garden-acl` without removing the basic garden surface
that remains core under ADR-002. The safe boundary is:

- **Core keeps basic gardens:** garden CRUD, admin/writer/reader membership,
  direct `garden_id` write validation, direct `garden_id` read validation, and
  scope mismatch rejection.
- **Plugin owns advanced cross-cutting ACL:** membership-derived auth ceilings,
  cross-surface recall/filter behavior, graph/recall visibility filters, and
  optional quarantine moderation extensions if they are not retained by the
  quarantine-garden core surface.

This is narrower than "move `garden_acl.py` wholesale." That module also holds
the helpers needed by core garden CRUD and by quarantine moderation.

## Current Core Touchpoints

| Surface | Files | Current behavior | PR 4e boundary |
|---|---|---|---|
| ACL helpers | `node/src/stigmem_node/garden_acl.py` | Resolves gardens/members and enforces admin/writer/reader plus quarantine moderator checks. | Split helpers by responsibility. Keep basic helper API core; plugin can wrap or own advanced helpers behind hooks/config. |
| Garden CRUD and membership | `node/src/stigmem_node/routes/gardens.py` | Creates gardens, auto-adds creator as admin, lists accessible gardens, manages members, prevents last-admin removal, handles quarantine promote/reject endpoints. | Keep basic garden CRUD/membership core. Quarantine-specific moderator role and promote/reject flow need a separate decision: retain with Spec-08 quarantine core, or gate as advanced ACL plugin behavior. |
| Fact assertion | `node/src/stigmem_node/routes/_facts_assert.py`, `node/src/stigmem_node/routes/facts/assertion.py` | Resolves `garden_id`, rejects missing garden or scope mismatch, requires writer/admin before persist. `pre_assert_authorize` already fires before implementation. | Keep basic direct write guard core. Use `pre_assert_authorize` for plugin-only advanced assertions or stricter policies. |
| Fact query | `node/src/stigmem_node/routes/facts/query.py` | `pre_recall_authorize` and `recall_filter` already fire. Direct `garden_id` queries require membership; global queries hide garden-tagged facts from non-members. | Keep direct `garden_id` query guard core. Move global visibility shaping to `recall_filter` only if the plugin is registered, or leave as core if ADR-002 treats hidden global garden facts as basic garden behavior. |
| Single fact read | `node/src/stigmem_node/routes/facts/single.py` | A fact with `garden_id` requires garden read membership. | Keep core; this is direct basic garden read protection. |
| Recall ranking | `node/src/stigmem_node/routes/recall/ranking.py` | Drops records whose `garden_id` is not visible to the caller. | Candidate for plugin `recall_filter`, because it is cross-cutting recall behavior. |
| Graph traversal | `node/src/stigmem_node/graph.py` | Drops edges in gardens the caller cannot see. | Candidate for plugin-owned filtering, but current 22-hook surface has no graph-specific hook. Use `recall_filter` only where graph results are represented as recall candidates; otherwise record a hook gap before moving behavior. |
| Subscription delivery | `node/src/stigmem_node/subscription_delivery.py` | Re-checks garden membership before delivery/replay payload exposure. | Security-sensitive. Current 22-hook surface has no subscription delivery filter hook. Do not remove until a hook exists or the replay path can reuse `recall_filter` safely. |
| OIDC exchange | `node/src/stigmem_node/routes/auth.py` | Caps OIDC session permissions based on garden membership role. | Advanced ACL behavior; move behind plugin registration or plugin-owned capability policy. `capability_check` may be a better future fit than the three PR 4e hooks. |
| Quarantine moderation | `node/src/stigmem_node/routes/quarantine.py`, `node/src/stigmem_node/routes/gardens.py` | Uses `quarantine:moderator`, garden membership, and quarantine garden flags. | Treat as Spec-08/Spec-05 quarantine core unless PR 4e explicitly absorbs moderator-role extensions. Avoid breaking quarantine tests while extracting advanced ACL. |

## Hook Mapping

| Hook | Existing call site | PR 4e usage |
|---|---|---|
| `pre_assert_authorize` | `routes/facts/assertion.py` before `assert_fact_impl` | Plugin can deny writes based on advanced garden ACL policies before core persistence. Core should still enforce basic garden write/scope rules for direct `garden_id` writes. |
| `pre_recall_authorize` | `routes/facts/query.py` before query rewrite | Plugin can deny advanced garden recall/filter requests up front. It should not be required for ordinary core reads. |
| `recall_filter` | `routes/facts/query.py` after recall pipeline/tombstone filter; recall pipeline hook sites also exist in plugin tests | Plugin can remove records/cards not visible under advanced garden ACL. This is the main extraction point for cross-cutting visibility shaping. |

## Migration Ownership

`node/migrations/004_gardens.sql` creates `gardens` and `garden_members`; this
belongs to basic garden support and should remain core.

`node/migrations/014_federation_trust.sql` extends gardens with the quarantine
flag, adds `quarantine:moderator`, and adds quarantine fact metadata. Those
tables/columns are shared with quarantine/source-trust behavior, not solely
advanced Memory Garden ACL. PR 4e should not move migration 014 wholesale unless
the quarantine-garden ownership decision changes.

No new mandatory core migration is required for the scaffold. If the plugin
needs plugin-owned metadata later, it should declare it through
`migration_register` under `experimental/memory-garden-acl`.

## Test Inventory

Primary tests:

- `node/tests/test_gardens.py` covers CRUD, membership, direct fact write/read
  ACL, hidden global query behavior, scope mismatch, and quarantine garden
  operations.
- `node/tests/test_subscriptions.py::test_replay_window_suppresses_garden_acl_blocked_events`
  covers subscription replay leakage.
- `node/tests/test_gardens.py::TestGardenFactACL` should be split during PR 4e:
  direct `garden_id` read/write protections remain core tests; global hiding or
  recall/graph behavior can move under plugin-loaded fixtures if classified as
  advanced.

Expected new tests:

- `node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py` for manifest,
  config, hooks, registration, and deterministic handler order.
- Plugin-loaded fixture tests proving `pre_assert_authorize`,
  `pre_recall_authorize`, and `recall_filter` behavior.
- Default-install tests proving basic gardens still work and no advanced
  cross-cutting ACL behavior is activated.

## Structural Gaps

The 22-hook surface named by the roadmap covers assertion and recall, but it
does not provide explicit hooks for garden CRUD/member management, graph
traversal, OIDC permission derivation, or subscription delivery. Therefore PR 4e
should not promise to extract every garden-related check through only
`pre_assert_authorize`, `pre_recall_authorize`, and `recall_filter`.

Recommended approach:

1. Keep basic garden CRUD/direct read/write checks in core.
2. Scaffold the plugin with the three roadmap hooks plus `migration_register`
   only if plugin-owned metadata is introduced.
3. Gate/move only the advanced cross-cutting behavior that can safely run
   through existing hooks.
4. Leave subscription replay and quarantine moderator enforcement in core until
   either a dedicated hook exists or follow-on issues explicitly rehome them.

This preserves the default-install security posture while avoiding a false
"core has no garden code" interpretation.
