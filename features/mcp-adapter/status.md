# MCP Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |

The MCP adapter source exists under `adapters/mcp` and includes TypeScript unit
tests. The package version remains independent from the alpha artifact set, so
release-line promotion requires packaging, connector, and security validation.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | MCP adapter source and connector guides existed as experimental adapter surface area. | `adapters/mcp`; `experimental/mcp-adapter/STATUS.md` |
| `0.9.xA` planned | Validate package alignment, host connector guides, and adapter security behavior before release promotion. | `docs/internal/feature-tracker.md`; `docs/internal/development.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Tool surface | Expose node operations through MCP tools. | Partial | `adapters/mcp/src/server.ts`; `adapters/mcp/README.md` |
| Unit coverage | Cover tool registration, argument coercion, session propagation, and recall channel output. | Partial | `adapters/mcp/src/server.test.ts` |
| Connector docs | Provide host-specific setup guidance. | Partial | `experimental/mcp-adapter/` |
| Package alignment | Align package metadata and release artifact policy with the active release line. | Open | `adapters/mcp/package.json`; `docs/compatibility-matrix.yaml` |
| Security certification | Validate recall rendering, instruction separation, and write-surface abuse cases. | Open | `features/mcp-adapter/security.md`; `docs/docs/security/model-certification.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- `stigmem-mcp` package metadata remains independent from the current alpha
  artifact set.
- Host connector guides need release-line verification before promotion.
- Live adapter/model certification is still required for prompt-injection and
  instruction-channel risks.
- Smoke testing depends on a running Stigmem node and host-specific MCP config.
