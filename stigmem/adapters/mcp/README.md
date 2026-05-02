# Stigmem MCP Server

Exposes [Stigmem](../../README.md) as an [MCP](https://modelcontextprotocol.io) server.
Any MCP-aware agent — Claude Code, Codex, or a custom host — can use Stigmem as a tool
without installing any SDK.

## Tools exposed

| Tool | Description |
|---|---|
| `assert_fact` | Write a typed fact to the node |
| `query_facts` | Query facts by entity / relation / scope |
| `resolve_contradiction` | Resolve a contradiction between two conflicting facts |
| `subscribe_scope` | Poll for recent facts in a scope (single-shot, cursor-based) |

## Setup

### Requirements

- Node.js ≥ 18
- A running Stigmem node (see `stigmem/node/README.md`)

### Install

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
```

### Configure in Claude Code

Add to `.claude/mcp_servers.json` (or the global MCP config):

```json
{
  "stigmem": {
    "command": "node",
    "args": ["/path/to/stigmem/adapters/mcp/dist/server.js"],
    "env": {
      "STIGMEM_URL": "http://localhost:8765",
      "STIGMEM_API_KEY": "sk-your-key-here"
    }
  }
}
```

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `STIGMEM_URL` | yes | — | Base URL of your Stigmem node |
| `STIGMEM_API_KEY` | no | — | API key if the node requires auth |
| `STIGMEM_POLL_LIMIT` | no | `50` | Facts per `subscribe_scope` call |

## Usage examples

Once connected, ask any MCP-aware agent:

```
# Write a decision fact
assert_fact(
  entity="decision:use-sqlite",
  relation="roadmap:status",
  value={"type":"string","v":"approved"},
  source="agent:cto"
)

# Query all active project constraints
query_facts(entity="project:acme-platform", relation="roadmap:constraint")

# Poll for recent public facts
subscribe_scope(scope="public")

# Resolve a contradiction
resolve_contradiction(
  conflict_id="stigmem:conflict:abc123",
  winning_fact_id="fact-001",
  resolution_note="CTO confirmed during board review 2026-05-02"
)
```

## Protocol notes

- `subscribe_scope` is a **single-shot poll**, not a streaming subscription. Call it
  repeatedly with the returned `cursor` to follow new facts over time.
- Facts are **immutable** once written. To update, assert a new fact for the same
  `(entity, relation, scope)`. To retract, call `assert_fact` with `confidence=0.0`.
- Scope filtering: `local` facts never leave the node. `public` facts are federatable.
  See spec §2.2 for the full scope semantics.

## Architecture

```
Claude Code / MCP host
      │  MCP (stdio)
      ▼
stigmem-mcp  (this package)
      │  HTTP
      ▼
Stigmem node  (stigmem/node)
      │
      ▼
 SQLite store
```

The MCP server is stateless — it translates MCP tool calls to HTTP requests against
the configured Stigmem node. No local state is held in the server process.
