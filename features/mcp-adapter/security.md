# MCP Adapter Security

## Threat Model Delta

The MCP adapter places Stigmem reads and writes inside an LLM tool boundary. It
can surface recalled facts to an agent and can write new facts on behalf of an
agent session. That makes prompt-injection handling, instruction-channel
separation, session attribution, and host configuration part of the adapter's
security posture.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| `R-05` | Recall responses preserve separate `content` and `instructions` channels and include a directive that recalled content is untrusted. | `adapters/mcp/src/server.ts`; `adapters/mcp/src/server.test.ts` |
| `R-15` | The adapter does not promote recalled instructions into privileged host instructions; host connector docs must preserve that boundary. | `adapters/mcp/README.md`; `features/mcp-adapter/spec.md` |
| `R-21` | Session propagation supports attribution for adapter-originated reads and writes. | `adapters/mcp/src/server.ts`; `adapters/mcp/src/server.test.ts` |

## Residual Risk

- MCP hosts can still render tool output unsafely. Host-specific connector
  guidance and certification evidence are required before promotion.
- API keys configured in MCP host files must be protected through local secret
  handling or host-specific secure storage.
- Tool calls that write facts depend on the node's auth, quota, audit, and
  scope enforcement. The adapter does not add an independent authorization
  layer.
- Package metadata is aligned for publication readiness, but registry
  publication remains held until live connector smoke, adapter security
  certification, dry-run evidence, and maintainer clearance are complete.

## Advisories and Findings

None currently recorded for the MCP adapter. The adapter contributes to R-05,
R-15, and R-21 validation because it is an external LLM tool surface.
