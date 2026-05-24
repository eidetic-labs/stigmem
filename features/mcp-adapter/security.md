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
| `R-15` | The adapter does not promote recalled instructions into privileged host instructions; adversarial recall payload tests confirm hostile role markers remain serialized tool data. | `adapters/mcp/src/server.test.ts`; `adapters/mcp/README.md`; `features/mcp-adapter/spec.md` |
| `R-21` | Session propagation supports attribution for adapter-originated reads and writes, while unknown credential-like tool arguments are ignored instead of forwarded as auth material. | `adapters/mcp/src/server.ts`; `adapters/mcp/src/server.test.ts` |
| Write-surface validation | Zod schemas reject invalid scope/write-mode combinations before the SDK write path is called. | `adapters/mcp/src/server.test.ts` |

## Residual Risk

- MCP hosts can still render tool output unsafely. Repo-local tests certify the
  adapter framing, but Codex CLI, Continue.dev, Cursor, and Zed UI rendering
  remain host-specific validation gaps before promotion.
- API keys configured in MCP host files must be protected through local secret
  handling or host-specific secure storage.
- Tool calls that write facts depend on the node's auth, quota, audit, and
  scope enforcement. The adapter does not add an independent authorization
  layer.
- Package metadata, repo-local protocol/security smoke, and npm dry-run
  evidence are aligned for publication readiness, but registry publication
  remains held until host UI smoke and maintainer clearance are complete.

## Carve-outs

The `0.9.0-alpha.8` MCP adapter does not implement:

- Rate limiting: there is no per-second or per-minute call cap. A misbehaving
  MCP client, or a host bug spamming tool calls, can exhaust upstream node
  capacity.
- Response size caps: large recall or query results are returned in full; the
  adapter does not enforce truncation beyond tool arguments and upstream node
  behavior.
- Concurrent connection limits: stdio is a single-host subprocess transport, so
  there is no adapter-level multi-connection listener to cap.
- Filesystem path hardening in tool arguments: current tool schemas do not
  accept filesystem paths. The adapter relies on Zod schemas and upstream node
  validation for the present six-tool surface.

These carve-outs are acceptable for the stdio subprocess model and alpha
distribution. They become required design gates if an HTTP or SSE transport is
added.

## Advisories and Findings

None currently recorded for the MCP adapter. The adapter contributes to R-05,
R-15, and R-21 validation because it is an external LLM tool surface.
