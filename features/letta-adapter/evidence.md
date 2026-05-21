# Letta Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/letta-adapter/adapter.py` | Letta client configuration, fact serialization, archival-memory push, batch push, pull, and parsing. |
| `experimental/letta-adapter/pyproject.toml` | Source package metadata for `stigmem-letta-adapter`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/letta-adapter/tests/test_letta_adapter.py` | Mocked Letta tests for serialization, parsing, environment configuration, push, batch push, pull, filtering, and missing-dependency errors. |
| `experimental/letta-adapter/tests/conftest.py` | Test path setup for importing the adapter module from the experimental source directory. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/letta-adapter/README.md` | Legacy adapter overview, setup, environment variables, usage, and invariants. |
| `experimental/letta-adapter/STATUS.md` | Legacy status statement now superseded by this feature record. |
| `docs/docs/operators/design-partner-notes.md` | Design-partner notes for Letta, including wake/sleep round-trip and synthesis feedback. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Live Letta server evidence is not complete.
- Package installation and dependency compatibility evidence remain deferred.
- The legacy docs refer to old adapter path examples in places and should be
  treated as historical implementation notes until the adapter is reactivated.
