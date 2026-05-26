# Letta Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/letta-adapter/src/stigmem_plugin_letta/adapter.py` | Letta client configuration, fact serialization, archival-memory push, batch push, pull, and parsing. |
| `experimental/letta-adapter/src/stigmem_plugin_letta/manifest.py` | Stigmem plugin discovery manifest. |
| `experimental/letta-adapter/pyproject.toml` | Package metadata for `stigmem-plugin-letta-adapter`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/letta-adapter/tests/test_letta_adapter.py` | Mocked Letta tests for serialization, parsing, environment configuration, push, batch push, pull, filtering, and missing-dependency errors. |
| `experimental/letta-adapter/tests/conftest.py` | Test path setup for importing the src-layout adapter package. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/letta-adapter/README.md` | Adapter overview, install, usage, enable/disable, and invariants. |
| `experimental/letta-adapter/spec.md` | Package projection for adapter semantics. |
| `experimental/letta-adapter/evidence.md` | Package-level validation evidence. |
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
- Live agent-memory behavior across Letta versions remains outside the v0.1.0
  automated release gate.
