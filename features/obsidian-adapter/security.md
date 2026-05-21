# Obsidian Adapter Security

## Threat Model Delta

The Obsidian adapter reads local markdown vault files, sends selected content to
a configured Stigmem node, and can write Stigmem facts back into local notes.
The plugin surface also stores API key material inside Obsidian plugin data.
This makes vault selection, ignored paths, local secret handling, and sync
provider behavior part of the adapter security posture.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| `R-07` | The docs warn that plugin API keys are stored locally and that `.obsidian/` should be excluded from cloud sync for private nodes. | `experimental/obsidian-adapter/plugin/README.md`; `experimental/obsidian-adapter/concept-plugin.md` |
| Sensitive vault content sync | The adapter supports ignored path patterns for `.obsidian/**`, templates, temporary files, and user-defined paths. | `experimental/obsidian-adapter/concept.md`; `experimental/obsidian-adapter/cli/src/stigmem_obsidian/config.py`; `experimental/obsidian-adapter/plugin/src/settings.ts` |
| Wrong node target | Both CLI and plugin require explicit node URL configuration before sync. | `experimental/obsidian-adapter/concept.md`; `experimental/obsidian-adapter/plugin/README.md` |

## Residual Risk

- Users must protect `.stigmem-sync.toml`, `.obsidian/plugins/stigmem/data.json`,
  and any local sync provider that can copy those files.
- Vault notes may contain personal or sensitive information. Users must review
  ignored paths and scope settings before enabling sync.
- The adapter can write managed sections into notes; users should keep backups
  when testing against real vaults.
- The adapter is experimental and not release-line certified.

## Advisories and Findings

None currently recorded for the adapter. The feature contributes to R-07 in the
threat model because of local plugin key storage.
