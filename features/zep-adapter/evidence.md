# Zep Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/zep-adapter/adapter.py` | Zep client configuration, fact-to-message encoding, Zep session write, query, and record conversion. |
| `experimental/zep-adapter/demo.py` | Demonstration flow that asserts a Stigmem fact, mirrors it into Zep, and reads extracted facts. |
| `experimental/zep-adapter/pyproject.toml` | Source package metadata for `stigmem-zep-adapter`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/zep-adapter/tests/test_zep_adapter.py` | Mocked Zep tests for message formatting, record shape, session writes, query behavior, limit handling, scope stamping, and Zep error handling. |
| `experimental/zep-adapter/tests/conftest.py` | Test path setup for importing the adapter module from the experimental source directory. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/zep-adapter/README.md` | Legacy adapter overview, setup, environment variables, usage, and protocol notes. |
| `experimental/zep-adapter/concept.md` | Legacy concept guidance for Stigmem/Zep federation. |
| `experimental/zep-adapter/STATUS.md` | Legacy status statement now superseded by this feature record. |
| `docs/docs/operators/design-partner-notes.md` | Design-partner notes for Zep, including session boundaries, history flooding, and confidence passthrough. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Live Zep Cloud or self-hosted Zep evidence is not complete.
- Package installation and dependency compatibility evidence remain deferred.
- The legacy docs refer to old adapter path examples in places and should be
  treated as historical implementation notes until the adapter is reactivated.
