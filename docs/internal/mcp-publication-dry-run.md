# MCP Adapter Publication Dry-Run

**Status:** complete for no-publication closeout
**Applies to:** `stigmem-mcp` `0.9.0-alpha.8`
**Last updated:** 2026-05-24

This record captures the MCP adapter publication dry-run after package metadata,
live protocol smoke, and repo-local adapter security certification landed. No
registry upload, release asset upload, tag, or provenance publication occurred.

## Publication Decision

| Surface | Decision | Reason |
| --- | --- | --- |
| `stigmem-mcp` | `hold` - do not publish | Package dry-runs pass, but Codex CLI, Continue.dev, Cursor, and Zed UI-level smoke have not been completed, and maintainer clearance for an npm registry action has not been granted. |

## Registry and Channel

| Field | Value |
| --- | --- |
| Registry | npm public registry |
| Package | `stigmem-mcp` |
| Version | `0.9.0-alpha.8` |
| Publish tag required | `alpha` |
| Provenance | `publishConfig.provenance=true`; dry-run command included `--provenance` |
| Access | `public` |

Because this is a prerelease package, npm requires an explicit tag. Future
publication commands must use `--tag alpha`; publishing without a tag is not
valid.

## Dry-Run Commands

The following commands were run from `adapters/mcp/`. They did not publish
artifacts.

```bash
pnpm --filter ./adapters/mcp build
npm pack --dry-run --json
npm publish --dry-run --provenance --tag alpha
```

## Dry-Run Artifact

| Field | Value |
| --- | --- |
| Filename | `stigmem-mcp-0.9.0-alpha.8.tgz` |
| Package size | `11963` bytes |
| Unpacked size | `45593` bytes |
| SHA-1 shasum | `13a0f9177ca99c58a814bdc4a6057adc93312a02` |
| Integrity | `sha512-TX5tSkI9FAslUHSem29wiV6dg3z4OrHc+crGBwK0DPs9lnslElQTqVhyuUXL6+LUft5B5xUdPn0roX5e8/IY+Q==` |

## Pack Contents

| Path | Mode | Purpose |
| --- | --- | --- |
| `README.md` | `0644` | Package setup and protocol notes. |
| `dist/server.d.ts` | `0644` | Type declarations. |
| `dist/server.js` | `0755` | Executable MCP server entry point and `bin` target. |
| `dist/server.js.map` | `0644` | Source map. |
| `package.json` | `0644` | Registry metadata. |

The dry-run initially exposed two packaging requirements:

- `dist/server.js` must be executable so npm preserves the `stigmem-mcp` bin.
- prerelease dry-runs must specify `--tag alpha`.

Both requirements are now captured in package metadata/scripts and this record.

## Rollback and Yank Plan

No rollback action is needed for this goal because nothing was published. If a
future maintainer-approved npm publication is executed and must be withdrawn:

1. Stop automation or release notes that point users to the package.
2. If within npm's unpublish window and policy permits, run `npm unpublish stigmem-mcp@0.9.0-alpha.8`.
3. If unpublish is unavailable or undesirable, run `npm deprecate stigmem-mcp@0.9.0-alpha.8 "<reason>"`.
4. Publish a corrective package only after a new PR records maintainer
   clearance, dry-run evidence, and post-publish verification.

## Remaining Gates

- Host UI smoke for Codex CLI, Continue.dev, Cursor, and Zed.
- Explicit maintainer clearance for npm publication.
- Post-publish install verification from a clean project, only after
  publication is approved.

### Publication-Scope Limitations

The MCP adapter ships stdio transport only in `0.9.0-alpha.8`. HTTP and SSE
transports defined by MCP are out of scope for this package state. Operators
using hosts that only support HTTP MCP servers cannot use this adapter until a
future HTTP transport lands.

HTTP transport remains a follow-up gate. Rate limits and connection caps become
required when the adapter accepts network clients instead of a single
editor-launched stdio host process.
