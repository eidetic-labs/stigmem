# Cognee Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/cognee-adapter/src/stigmem_plugin_cognee/adapter.py` | Serialization, Cognee configuration, assertion, batch assertion, query, and result normalization. |
| `experimental/cognee-adapter/demo.py` | Demonstration flow that asserts Stigmem facts, pushes them into Cognee, and queries the graph. |
| `experimental/cognee-adapter/pyproject.toml` | Source package metadata for `stigmem-plugin-cognee-adapter`. |
| `experimental/cognee-adapter/src/stigmem_plugin_cognee/manifest.py` | Stigmem plugin discovery manifest for `cognee-adapter`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/cognee-adapter/tests/test_cognee_adapter.py` | Mocked Cognee tests for serialization, parsing, normalization, environment configuration, assertion, batch assertion, query, and missing-dependency errors. |
| `experimental/cognee-adapter/tests/conftest.py` | Test path setup for importing the src-layout adapter package. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/cognee-adapter/README.md` | Legacy adapter overview, setup, environment variables, usage, search types, and invariants. |
| `experimental/cognee-adapter/STATUS.md` | Legacy status statement now superseded by this feature record. |
| `docs/docs/operators/design-partner-notes.md` | Design-partner notes for Cognee, including namespace, provenance, and fuzzy-resolution feedback. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Live Cognee runtime evidence is not complete.
- Live Cognee runtime evidence is not complete.
- Provider-specific extraction quality remains out of scope for v0.1.0.
