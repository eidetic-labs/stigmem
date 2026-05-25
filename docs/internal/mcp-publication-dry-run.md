# MCP Adapter Publication Dry-Run

**Status:** complete for scoped npm first-publication clearance
**Applies to:** `@eidetic-labs/stigmem-mcp` `0.1.0`
**Last updated:** 2026-05-25

This record captures the MCP adapter publication dry-run after package metadata,
live protocol smoke, repo-local adapter security certification, and maintainer
clearance landed. No registry upload, release asset upload, tag, or provenance
publication occurred during the dry run.

## Publication Decision

| Surface | Decision | Reason |
| --- | --- | --- |
| `@eidetic-labs/stigmem-mcp` | `publish-now` | Package dry-runs pass, Codex CLI / Claude Code host UI smoke has passed, Gemini CLI host UI smoke completed with a final-response caveat, and maintainer clearance was granted for the scoped npm package at independent version `0.1.0`. Continue.dev, Cursor, and Zed connector guides are experimental and unvalidated for `0.1.0`; they are not publication blockers. |

## Registry and Channel

| Field | Value |
| --- | --- |
| Registry | npm public registry |
| Package | `@eidetic-labs/stigmem-mcp` |
| Version | `0.1.0` |
| Publish tag required | `alpha` |
| Provenance | `publishConfig.provenance=true`; dry-run command included `--provenance` |
| Access | `public` |
| Runtime SDK dependency | `@eidetic-labs/stigmem-ts@^0.9.0-alpha.8` |

The MCP adapter is versioned independently from the Stigmem project semver
line. The initial npm publication still uses the `alpha` dist-tag because the
adapter and host support matrix remain preview-quality.

## Dry-Run Commands

The following commands were run from `adapters/mcp/`. They did not publish
artifacts.

```bash
pnpm --filter ./adapters/mcp build
pnpm --filter ./adapters/mcp test
npm pack --dry-run --json
npm publish --dry-run --provenance --access public --tag alpha
```

## Dry-Run Artifact

| Field | Value |
| --- | --- |
| Filename | `eidetic-labs-stigmem-mcp-0.1.0.tgz` |
| Package size | `12294` bytes |
| Unpacked size | `46602` bytes |
| SHA-1 shasum | `7aa71c1970ad92df794a370366e0c19689a53002` |
| Integrity | `sha512-DEGnbMLTbXmClbeGJcok3F7ylJ7wS0n686R3ZLA2cP6Zx6bcX9axTkA8NwaGkmStn0EjuGuNkugSz0Ksyt1Buw==` |

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

No rollback action is needed for this dry run because nothing was published. If
the maintainer-approved npm publication is executed and must be withdrawn:

1. Stop automation or release notes that point users to the package.
2. If within npm's unpublish window and policy permits, run `npm unpublish @eidetic-labs/stigmem-mcp@0.1.0`.
3. If unpublish is unavailable or undesirable, run `npm deprecate @eidetic-labs/stigmem-mcp@0.1.0 "<reason>"`.
4. Publish a corrective package only after a new PR records maintainer
   clearance, dry-run evidence, and post-publish verification.

## Remaining Gates

- First registry publication with an npm token or Trusted Publisher.
- Post-publish install verification from a clean project.

Continue.dev, Cursor, and Zed connector guides remain experimental and
unvalidated in this release line because those host UIs are not available in the
maintainer environment for the `0.1.0` clearance gate. They are not
publication blockers only if package and release material scope validated host
support to Codex CLI, Claude Code, Gemini CLI with its final-response caveat,
and the repo-local MCP protocol smoke.

### Publication-Scope Limitations

The MCP adapter ships stdio transport only in `0.1.0`. HTTP and SSE
transports defined by MCP are out of scope for this package state. Operators
using hosts that only support HTTP MCP servers cannot use this adapter until a
future HTTP transport lands.

HTTP transport remains a follow-up gate. Rate limits and connection caps become
required when the adapter accepts network clients instead of a single
editor-launched stdio host process.
