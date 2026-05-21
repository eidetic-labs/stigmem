# Obsidian Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/obsidian-adapter/cli/src/stigmem_obsidian/` | Python CLI/daemon parser, config, syncer, vault reader, and vault writer. |
| `experimental/obsidian-adapter/cli/pyproject.toml` | `stigmem-obsidian` package metadata and CLI entry point. |
| `experimental/obsidian-adapter/plugin/src/` | Obsidian plugin settings, parser, syncer, client, recall view, and plugin entry point. |
| `experimental/obsidian-adapter/plugin/package.json` | Plugin package metadata and build/test scripts. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/obsidian-adapter/cli/tests/` | Python config, parser, syncer, and vault-writer behavior. |
| `experimental/obsidian-adapter/plugin/src/parser.test.ts` | Plugin parser behavior. |
| `experimental/obsidian-adapter/plugin/src/settings.test.ts` | Plugin settings and ignored-path behavior. |
| `experimental/obsidian-adapter/plugin/src/syncer.test.ts` | Plugin sync behavior. |

## Docs

| Path | Coverage |
| --- | --- |
| `experimental/obsidian-adapter/concept.md` | CLI/daemon architecture, configuration, sync behavior, and security notes. |
| `experimental/obsidian-adapter/concept-plugin.md` | Plugin-specific concept guidance. |
| `experimental/obsidian-adapter/plugin/README.md` | Plugin installation, features, settings, compatibility, and security notes. |
| `experimental/obsidian-adapter/tutorial-self-host.md` | Self-hosted vault workflow. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Live-vault smoke evidence is not complete.
- Package and plugin publication evidence remain deferred.
- Security review for local API key storage and sync-provider leakage remains
  required before promotion.
