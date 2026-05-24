# MCP Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |
| Publication state | `hold` - package metadata, live protocol smoke, and repo-local adapter security regressions are aligned; host UI smoke, dry-run evidence, and maintainer publication clearance remain incomplete. |

The MCP adapter source exists under `adapters/mcp` and includes TypeScript unit
tests. The package metadata is aligned to the current alpha release line, and
the repo-local stdio smoke now validates against a live node. Focused adapter
security regressions cover recall framing, malformed write rejection, and
credential/session boundaries. Publication still requires host UI smoke,
dry-run, and maintainer clearance validation.

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
| Connector docs | Provide host-specific setup guidance. | Partial; repo-local smoke validated, host UI launches still open | `experimental/mcp-adapter/`; `adapters/mcp/tests/smoke.sh` |
| Package alignment | Align package metadata and release artifact policy with the active release line. | Complete for metadata; publication still held | `adapters/mcp/package.json`; `release/version-surfaces.yaml`; `docs/compatibility-matrix.yaml` |
| Security certification | Validate recall rendering, instruction separation, and write-surface abuse cases. | Complete for repo-local adapter framing; live model certification remains separate | `features/mcp-adapter/security.md`; `adapters/mcp/src/server.test.ts`; `docs/docs/security/model-certification.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- Host connector guides need UI-level verification in Codex CLI, Continue.dev,
  Cursor, and Zed before promotion.
- Live model certification remains required for provider/model behavior under
  ADR-015; adapter framing regression coverage is complete for the current
  tool surface.
- Smoke testing depends on a running Stigmem node and host-specific MCP config.
- Registry publication remains blocked until dry-run evidence and maintainer
  clearance are recorded.
