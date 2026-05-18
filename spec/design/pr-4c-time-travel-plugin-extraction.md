# PR 4c Time-Travel Plugin Extraction Analysis

Issue: [#308](https://github.com/eidetic-labs/stigmem/issues/308)
Parent: [#307](https://github.com/eidetic-labs/stigmem/issues/307)

## Decision

PR 4c should proceed as an extraction and gating effort, not as a no-op
validation pass.

Unlike PR 4b CIDs, time-travel is not a core feature under the current roadmap.
`Spec-X3-Time-Travel-Queries` remains experimental, while the default install
currently exposes active `as_of` behavior on facts and recall. PR 4c therefore
needs to move that behavior behind `stigmem-plugin-time-travel` registration so
the default install has no time-travel surface.

Plugin artifact signing, publishing, and launch evidence remain outside this
step. Those tasks stay deferred until the broader plugin set is built and ready
for release packaging.

## Current Core Surface

The current active implementation is present in these locations:

- `node/src/stigmem_node/routes/facts/query.py`
  - defines `_validate_as_of`;
  - defines `_query_facts_as_of_impl`;
  - exposes the `as_of` query parameter on `GET /v1/facts`;
  - branches into the historical fact query when `as_of` is present;
  - uses `pre_recall_authorize`, `pre_recall_rewrite`, and
    `post_recall_audit` around both normal and `as_of` fact-query paths.
- `node/src/stigmem_node/routes/recall/orchestration.py`
  - imports `_recall_as_of_impl`;
  - branches to `_handle_as_of_recall` when `RecallRequest.as_of` is present.
- `node/src/stigmem_node/routes/recall/as_of.py`
  - implements the historical recall query, ranking, tombstone filtering, and
    response packing.
- `node/src/stigmem_node/models/recall.py`
  - exposes `RecallRequest.as_of`.
- `node/src/stigmem_node/models/facts.py`
  - includes `QueryResponse.tombstone_notices`, which is used by historical
    fact queries.
- `node/src/stigmem_node/settings.py`
  - exposes `as_of_retention_floor`.
- `data/conformance/v2.0/24_time_travel.json`
  - validates active default-install `as_of` behavior.
- `node/tests/time_travel/test_phase13_time_travel_cid.py`
  - interleaves CID tests with active time-travel tests for fact query, recall,
    retraction, expiry, tombstones, and legal hold.
- `docs/openapi/stigmem.json`
  - documents `as_of` on default public API shapes.
- `experimental/time-travel/concept.md`
  - describes time-travel as currently supported rather than dormant or
    plugin-gated.

## Extraction Strategy

PR 4c should use the existing 22-hook infrastructure and keep the extraction
narrow:

1. Add a `stigmem-plugin-time-travel` package under
   `experimental/time-travel/`.
2. Move the timestamp validation and historical query behavior out of the
   default facts and recall route path, or gate the route branch so it cannot
   execute unless the plugin is registered.
3. Use `pre_recall_authorize` to deny `as_of` requests when the plugin is not
   registered or when the caller lacks the required capability.
4. Use `pre_recall_rewrite` only for request normalization and plugin-owned
   query shaping. It should not make default core perform time-travel behavior.
5. Keep `post_recall_audit` for historical-query outcomes so the plugin remains
   observable.
6. Use `migration_register` only if the plugin needs plugin-owned schema. The
   current implementation relies on the existing `fact_retractions` table; PR
   4c should avoid inventing a new migration unless implementation work exposes
   a concrete plugin-owned storage need.
7. Split tests so default-install behavior proves no active time-travel surface,
   while plugin-loaded tests prove the previous `as_of` behavior still works.
8. Move or mark `data/conformance/v2.0/24_time_travel.json` as plugin-required
   so default conformance does not require experimental time-travel.

## Capabilities And Configuration

The plugin should request only the capabilities needed to preserve the current
behavior:

- `facts.read` for historical fact queries.
- `recall.read` for historical recall.
- `config.read` for retention-floor configuration.
- `audit.emit` if plugin-owned audit emission is added beyond the existing
  recall audit hook.

The plugin configuration should default to disabled behavior unless the plugin
is explicitly registered:

- `enabled: false`
- `allow_fact_query_as_of: false`
- `allow_recall_as_of: false`
- `retention_floor: null`

The implementation issue may refine the exact field names, but PR 4c should
preserve the roadmap invariant: no plugin, no time-travel.

## Risks And Open Edges

Time-travel depends on tombstone semantics, while tombstones are scheduled for
PR 4d. PR 4c should preserve the behavior that exists today when tombstone code
is available, but it should not expand into a tombstone extraction or promotion
effort.

Generated API documentation and the integrator concept page currently overstate
time-travel availability. PR 4c closeout should update those surfaces after the
implementation and validation PRs land.

The artifact-publishing task is deliberately deferred. The implementation PRs
should create and validate plugin code, but launch evidence belongs to the
later plugin packaging pass after all planned plugins are built.
