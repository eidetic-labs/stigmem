# Gemini Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/gemini-adapter/src/stigmem_plugin_gemini/adapter.py` | Gemini function declarations, Stigmem dispatch, environment configuration, and optional Gemini run loop. |
| `experimental/gemini-adapter/src/stigmem_plugin_gemini/manifest.py` | Stigmem plugin discovery manifest. |
| `experimental/gemini-adapter/pyproject.toml` | Package metadata for `stigmem-plugin-gemini-adapter`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/gemini-adapter/tests/test_gemini_adapter.py` | Tests for function declarations, environment configuration, dispatch behavior, HTTP mocking, and error handling. |
| `experimental/gemini-adapter/tests/conftest.py` | Test path setup for importing the src-layout adapter package. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/gemini-adapter/README.md` | Adapter overview, install, usage, enable/disable, and protocol notes. |
| `experimental/gemini-adapter/spec.md` | Package projection for adapter semantics. |
| `experimental/gemini-adapter/evidence.md` | Package-level validation evidence. |

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
- Live Gemini API evidence is not complete.
- Live model acceptance across Gemini model families remains outside the v0.1.0
  automated release gate.
