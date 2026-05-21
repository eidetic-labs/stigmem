# Obsidian Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |

The adapter source exists for both CLI/daemon and plugin surfaces, but it
remains experimental and outside the current alpha artifact set. Promotion
requires package validation, plugin validation, threat-model review, and
live-vault smoke evidence.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Obsidian adapter source and documentation existed as experimental adapter surface area. | `experimental/obsidian-adapter/STATUS.md`; `experimental/obsidian-adapter/` |
| `0.9.xA` planned | Validate CLI/package behavior, plugin behavior, key-storage guidance, and live-vault sync before promotion. | `docs/internal/feature-tracker.md`; `docs/compatibility-matrix.yaml` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| CLI sync surface | Parse vault notes, push facts, pull managed sections, and support dry-run/watch. | Partial | `experimental/obsidian-adapter/cli/src/stigmem_obsidian/` |
| Plugin sync surface | Run inside Obsidian and share parser/sync semantics with the CLI. | Partial | `experimental/obsidian-adapter/plugin/src/` |
| Test coverage | Cover parser, config, syncer, writer, plugin parser/settings/syncer behavior. | Partial | `experimental/obsidian-adapter/cli/tests/`; `experimental/obsidian-adapter/plugin/src/*.test.ts` |
| Security review | Validate key storage, ignored path guidance, and vault sync boundary. | Open | `features/obsidian-adapter/security.md`; `docs/docs/security/scenarios.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- The adapter is not shipped in the current alpha artifact set.
- Live-vault smoke evidence is not complete.
- Plugin registry approval and packaging evidence are not complete.
- API key storage remains operator/user responsibility.
