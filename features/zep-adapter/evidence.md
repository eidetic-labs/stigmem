# Zep Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/zep-adapter/src/stigmem_plugin_zep/adapter.py` | Zep client configuration, fact-to-message encoding, Zep session write, query, and record conversion. |
| `experimental/zep-adapter/src/stigmem_plugin_zep/manifest.py` | Plugin discovery manifest for `stigmem-plugin-zep-adapter` v0.1.0. |
| `experimental/zep-adapter/demo.py` | Demonstration flow that asserts a Stigmem fact, mirrors it into Zep, and reads extracted facts. |
| `experimental/zep-adapter/pyproject.toml` | Package metadata, optional Zep/demo extras, entry point, and build configuration. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/zep-adapter/tests/test_zep_adapter.py` | Mocked Zep tests for message formatting, record shape, session writes, query behavior, limit handling, scope stamping, and Zep error handling. |
| `experimental/zep-adapter/tests/conftest.py` | Test path setup for importing the src-layout adapter package and workspace dependencies. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/zep-adapter/README.md` | Package overview, install, enable/disable, test, usage, environment variables, and protocol notes. |
| `experimental/zep-adapter/concept.md` | Concept guidance for Stigmem/Zep federation. |
| `experimental/zep-adapter/STATUS.md` | Package publication gate status. |
| `docs/docs/operators/design-partner-notes.md` | Design-partner notes for Zep, including session boundaries, history flooding, and confidence passthrough. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `Spec-X7-Zep-Adapter` is represented in the protocol projection. |

## Evidence Gaps

- Live Zep Cloud or self-hosted Zep evidence is not complete.
- Session authorization, redaction, retention, and deduplication policy are
  caller-owned integration concerns.
