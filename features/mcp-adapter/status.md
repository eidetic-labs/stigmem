# MCP Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |
| Publication state | `publish-now` - scoped package metadata, live protocol smoke, repo-local adapter security regressions, npm dry-run evidence, Codex CLI / Claude Code host UI smoke, Gemini CLI smoke with caveat, and maintainer publication clearance are aligned for `@eidetic-labs/stigmem-mcp@0.1.0`. |

The MCP adapter source exists under `adapters/mcp` and includes TypeScript unit
tests. The npm package is independently versioned from the Stigmem project
release line, and the repo-local stdio smoke validates against a live node.
Focused adapter security regressions cover recall framing, malformed write
rejection, and credential/session boundaries. npm dry-runs pass with
`--access public --tag alpha` and provenance enabled. Codex CLI and Claude Code
host UI smoke passes. Gemini CLI host UI smoke completed with a final-response
caveat. Continue.dev, Cursor, and Zed connector guides remain experimental and
unvalidated for `0.1.0`.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | MCP adapter source and connector guides existed as experimental adapter surface area. | `adapters/mcp`; `experimental/mcp-adapter/STATUS.md` |
| `0.9.xA` planned | Validate package alignment, host connector guides, and adapter security behavior before release promotion. | `docs/internal/feature-tracker.md`; `docs/internal/development.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Tool surface | Expose node operations through MCP tools. | Complete for current six-tool surface | `adapters/mcp/src/server.ts`; `adapters/mcp/README.md`; `adapters/mcp/tests/smoke.sh` |
| Unit coverage | Cover tool registration, argument coercion, session propagation, and recall channel output. | Complete for current adapter logic | `adapters/mcp/src/server.test.ts` |
| Connector docs | Provide host-specific setup guidance. | Partial; Codex CLI and Claude Code are validated for this alpha; Gemini CLI is caveated; Continue.dev, Cursor, and Zed are unvalidated experimental guides | `experimental/mcp-adapter/`; `adapters/mcp/tests/smoke.sh`; `docs/internal/mcp-host-ui-smoke-2026-05-24.md` |
| Package alignment | Align package metadata and release artifact policy with the independent npm package line. | Complete for scoped `0.1.0` package metadata | `adapters/mcp/package.json`; `docs/compatibility-matrix.yaml` |
| Security certification | Validate recall rendering, instruction separation, and write-surface abuse cases. | Complete for repo-local adapter framing; live model certification remains separate | `features/mcp-adapter/security.md`; `adapters/mcp/src/server.test.ts`; `docs/docs/security/model-certification.md` |
| Host UI smoke | Validate the adapter inside targeted MCP hosts before any host-specific alpha publication claim. | Complete for Codex CLI and Claude Code; Gemini CLI complete with final-response caveat | `docs/internal/mcp-host-ui-smoke-2026-05-24.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- Continue.dev, Cursor, and Zed connector guides are not validated for
  `0.1.0`; do not claim supported host status for those editors until a
  future smoke record captures real results.
- Live model certification remains required for provider/model behavior under
  ADR-015; adapter framing regression coverage is complete for the current
  tool surface.
- Smoke testing depends on a running Stigmem node and host-specific MCP config.
- Registry publication still requires the actual npm first-publish action and
  post-publish install verification.
