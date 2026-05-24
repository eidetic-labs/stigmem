# MCP Adapter Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `adapters/mcp/src/server.ts` | MCP server, tool definitions, argument schemas, session propagation, recall output framing, and SDK call handling. |
| `adapters/mcp/package.json` | Package metadata, runtime dependencies, and test/build scripts. |
| `adapters/mcp/README.md` | Adapter setup, tool list, environment variables, and protocol notes. |
| `adapters/mcp/tests/smoke.sh` | Node-backed smoke-test entry point. |
| `release/version-surfaces.yaml` | Version-consistency registration for `adapters/mcp/package.json`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `adapters/mcp/src/server.test.ts` | Tool registration, JSON argument coercion, session propagation, recall channel separation, lint calls, and error reporting. |
| `pnpm --filter "./adapters/mcp" test` | Package-local Vitest entry point. |
| `pnpm --filter "./adapters/mcp" type-check` | TypeScript type-check entry point. |
| `pnpm --filter "./adapters/mcp" build` | TypeScript build for the package runtime entry point. |
| `npm pack --dry-run --json` from `adapters/mcp/` | Package file allowlist and registry metadata dry-run; current package contains `README.md`, `dist/server.js`, `dist/server.js.map`, `dist/server.d.ts`, and `package.json`. |
| `python3 scripts/check_version_consistency.py` | Confirms `stigmem-mcp` package metadata is aligned with the active release line. |

## Connector Docs

| Path | Coverage |
| --- | --- |
| `experimental/mcp-adapter/connector-codex-cli.md` | Codex CLI MCP configuration. |
| `experimental/mcp-adapter/connector-continue-dev.md` | Continue.dev MCP configuration. |
| `experimental/mcp-adapter/connector-cursor.md` | Cursor MCP configuration. |
| `experimental/mcp-adapter/connector-zed.md` | Zed MCP configuration. |
| `docs/docs/sdks/connectors/index.md` | Public connector index. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Package metadata is aligned; artifact publication evidence is not complete.
- Host-specific connector guides need fresh smoke evidence.
- Live model/adapter certification evidence is still required before promotion.
