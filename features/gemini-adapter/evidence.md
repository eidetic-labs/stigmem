# Gemini Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/gemini-adapter/adapter.py` | Gemini function declarations, Stigmem dispatch, environment configuration, and optional Gemini run loop. |
| `experimental/gemini-adapter/pyproject.toml` | Source package metadata for `stigmem-gemini-adapter`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/gemini-adapter/tests/test_gemini_adapter.py` | Tests for function declarations, environment configuration, dispatch behavior, HTTP mocking, and error handling. |
| `experimental/gemini-adapter/tests/conftest.py` | Test path setup for importing the adapter module from the experimental source directory. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/gemini-adapter/README.md` | Legacy adapter overview, setup, usage, and protocol notes. |
| `experimental/gemini-adapter/concept.md` | Legacy concept guidance for Gemini function-calling integration. |
| `experimental/gemini-adapter/STATUS.md` | Legacy status statement now superseded by this feature record. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Live Gemini API evidence is not complete.
- Package installation and dependency compatibility evidence remain deferred.
- The legacy docs refer to old adapter path examples in places and should be
  treated as historical implementation notes until the adapter is reactivated.
