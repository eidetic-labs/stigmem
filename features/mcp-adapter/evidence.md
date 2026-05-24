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
| `adapters/mcp/src/server.test.ts` | Tool registration, JSON argument coercion, session propagation, recall channel separation, adversarial recall framing, malformed write rejection, credential-like argument filtering, lint calls, and error reporting. |
| `pnpm --filter "./adapters/mcp" test` | Package-local Vitest entry point. |
| `pnpm --filter "./adapters/mcp" exec vitest run src/server.test.ts --reporter verbose` | Focused MCP security regression evidence; 14 tests passed including adversarial recall, malformed write, and credential-boundary cases. |
| `pnpm --filter "./adapters/mcp" type-check` | TypeScript type-check entry point. |
| `pnpm --filter "./adapters/mcp" build` | TypeScript build for the package runtime entry point. |
| `npm pack --dry-run --json` from `adapters/mcp/` | Package file allowlist and registry metadata dry-run; current package contains `README.md`, executable `dist/server.js`, `dist/server.js.map`, `dist/server.d.ts`, and `package.json`. |
| `npm publish --dry-run --provenance --tag alpha` from `adapters/mcp/` | npm publication dry-run only; no registry upload occurred. Confirms prerelease publication requires the `alpha` tag. |
| `python3 scripts/check_version_consistency.py` | Confirms `stigmem-mcp` package metadata is aligned with the active release line. |
| `docs/internal/mcp-publication-dry-run.md` | Captures dry-run hashes, pack contents, registry/channel plan, rollback/yank plan, and no-publication disposition. |
| `docs/internal/mcp-host-ui-smoke-2026-05-24.md` | Manual host UI smoke execution record. Codex CLI is the required `0.9.0-alpha.8` host UI gate; Continue.dev, Cursor, and Zed are explicitly unvalidated experimental connector guides. |
| `STIGMEM_AUTH_REQUIRED=false STIGMEM_DB_PATH=/private/tmp/stigmem-mcp-smoke-final.db STIGMEM_PORT=8765 uv run python -c 'from stigmem_node.main import run; run()'` | Starts a local unauthenticated loopback node for live MCP smoke validation. |
| `STIGMEM_URL=http://localhost:8765 bash adapters/mcp/tests/smoke.sh` | Live MCP protocol smoke passed against a local node: initialize, six-tool discovery, `assert_fact`, `query_facts`, `recall`, `lint_scope`, and session-aware calls. |

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

- Package metadata, live protocol smoke, adapter security regressions, and npm dry-run evidence are aligned; artifact publication is still not approved or executed.
- Host-specific connector guides have been reviewed against the local stdio smoke path, and the host UI smoke execution record exists. Codex CLI UI-level launch evidence is still required for Codex-scoped alpha publication clearance. Continue.dev, Cursor, and Zed UI-level launches remain unvalidated and must not be described as supported until a future smoke record captures real pass/fail evidence.
- Live model certification remains separate from adapter framing certification; no provider/model is certified until reviewed ADR-015 result JSON is committed.
