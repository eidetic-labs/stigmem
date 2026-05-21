# Fuzzy Resolver Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `node/src/stigmem_node/recall/entity_resolver.py` | Three-layer resolver implementation used by the entity-resolution API. |
| `node/src/stigmem_node/recall/fuzzy_resolver.py` | Alias-focused compatibility resolver used by assertion and query paths. |
| `node/src/stigmem_node/routes/resolver.py` | Authenticated `GET /v1/entities/resolve` route. |
| `node/src/stigmem_node/routes/aliases.py` | Authenticated alias registration, listing, and deletion routes. |
| `node/src/stigmem_node/routes/facts/query.py` | Query path compatibility for canonical and aliased entity/source filters. |
| `node/src/stigmem_node/migrate.py` | Migration sweep that populates canonical alias rows from existing facts. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `node/tests/recall/test_fuzzy_resolver.py` | Alias registration, listing, filtering, deletion, migration-alias protection, fact-query alias compatibility, and entity resolver layer 2 API behavior. |
| `node/tests/auth/test_peer_auth_resolver_b2.py` | Malformed inputs, canonical hits, layer 3 fuzzy candidates, and alias hits. |
| `node/tests/lifecycle/test_migrate.py` | Migration alias population from non-canonical entity and source URIs. |
| `node/tests/routes/test_facts.py` | Canonical entity query behavior without aliases. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- No benchmark or evaluation dataset currently measures false-positive and
  false-negative behavior.
- No operator-runbook evidence exists for tuning the layer 3 threshold.
