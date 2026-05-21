# MCP Adapter Spec

## Scope

The MCP adapter wraps Stigmem node capabilities as MCP tools. It does not define
the MCP protocol itself and does not own node API semantics. It owns the adapter
tool surface, host configuration expectations, session propagation, and recall
channel handling.

This feature covers:

- the `stigmem-mcp` TypeScript package under `adapters/mcp`;
- stdio MCP server startup;
- tool registration for fact write, query, recall, contradiction resolution,
  scope polling, and scope linting;
- conversion from MCP tool arguments into SDK/client calls;
- environment-based node connection settings;
- connector guidance for MCP-capable hosts.

## Tool Surface

| Tool | Behavior |
| --- | --- |
| `assert_fact` | Write a typed fact to the configured node. |
| `query_facts` | Query facts by entity, relation, scope, source, confidence, and cursor. |
| `recall` | Retrieve recall results while preserving content and instruction channels. |
| `resolve_contradiction` | Resolve a known contradiction by selecting a winner or asserting a fresh value. |
| `subscribe_scope` | Poll a scope for facts using cursor-based pagination; this is not streaming. |
| `lint_scope` | Run read-only knowledge-health checks for a scope. |

## Configuration

| Setting | Required | Purpose |
| --- | --- | --- |
| `STIGMEM_URL` | Yes | Base URL of the Stigmem node. |
| `STIGMEM_API_KEY` | No | API key when node auth is required. |
| `STIGMEM_SESSION_ID` | No | Stable session id for adapter-originated reads and writes. |
| `STIGMEM_POLL_LIMIT` | No | Default fact limit for `subscribe_scope`. |

## Recall Channel Contract

The adapter must keep recalled `content` and `instructions` arrays separate and
return a system prompt directive that tells hosts to treat recalled content as
untrusted data. Hosts must not concatenate recalled facts into higher-priority
instructions.

## Non-Goals

- Defining or versioning MCP itself.
- Making the adapter part of the stable default node surface.
- Owning node API behavior or feature semantics behind each tool.
- Claiming package-version alignment with the current alpha artifact set before
  release-line validation is complete.

## Canonical Spec Assignment

There is no Spec-X assignment for the MCP adapter. It is an implementation
adapter around existing node and SDK behavior, not a standalone Stigmem
protocol module.
