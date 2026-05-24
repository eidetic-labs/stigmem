# Stigmem MCP Server

Exposes [Stigmem](../../README.md) as an [MCP](https://modelcontextprotocol.io) server.
Any stdio-capable MCP host can launch this adapter, but the `0.9.0-alpha.9`
publication gate only validates Codex CLI, Claude Code, and the repo-local MCP
protocol smoke. Gemini CLI has passed MCP tool execution with a host
final-response caveat. Continue.dev, Cursor, Zed, and custom-host connector use
is experimental until a host-specific smoke record exists.

## Tools exposed

| Tool | Description |
|---|---|
| `assert_fact` | Write a typed fact to the node |
| `query_facts` | Query facts by entity / relation / scope |
| `recall` | Retrieve channel-separated recall context |
| `resolve_contradiction` | Resolve a contradiction between two conflicting facts |
| `subscribe_scope` | Poll for recent facts in a scope (single-shot, cursor-based) |
| `lint_scope` | Health-check sweep — detect contradictions, stale facts, orphans, broken refs (read-only; `Spec-20-Lint-Semantics`) |

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

The package metadata is aligned to `0.9.0-alpha.9` for publication readiness,
but registry publication is still held. Use the workspace build until the
feature record records explicit maintainer clearance. Continue.dev, Cursor, and
Zed guides remain unvalidated for this alpha package state. Gemini CLI users
should review the host caveat in the MCP smoke record before relying on clean
final-response rendering.

### Configure in Claude Code

Add to `.claude/mcp_servers.json` (or the global MCP config):

```json
{
  "stigmem": {
    "command": "node",
    "args": ["/path/to/stigmem/adapters/mcp/dist/server.js"],
    "env": {
      "STIGMEM_URL": "http://localhost:8765",
      "STIGMEM_API_KEY": "sk-your-key-here",
      "STIGMEM_SESSION_ID": "mcp:agent-01"
    }
  }
}
```

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `STIGMEM_URL` | yes | — | Base URL of your Stigmem node |
| `STIGMEM_API_KEY` | no | — | API key if the node requires auth |
| `STIGMEM_SESSION_ID` | no | generated per call | Optional stable session id override propagated as `Stigmem-Session` for reads and writes |
| `STIGMEM_POLL_LIMIT` | no | `50` | Facts per `subscribe_scope` call |

## Security Model

The Stigmem MCP server is an editor-launched stdio subprocess. Its security
model assumes:

1. The host has already authorized the subprocess launch.
2. `STIGMEM_API_KEY`, read at startup, grants the subprocess its permissions on
   the configured Stigmem node.
3. Every MCP tool call routed to this subprocess executes under the same key.

Treat the subprocess as equivalent to running `stigmem-node` CLI commands
directly. Do not share one MCP subprocess across mutually untrusted projects,
operators, or host profiles; each trust boundary should get its own subprocess
and key.

The subprocess does not authenticate individual MCP requests beyond the host's
launch authorization. Receipts and audit events record the node identity derived
from `STIGMEM_API_KEY`; pass `session_id` per call when the host can provide
conversation-specific attribution. If no `session_id` is provided, the adapter
generates one per tool call unless `STIGMEM_SESSION_ID` pins a process-level
override.

This is not a hostile multi-tenant boundary and not a per-conversation auth
mechanism. Those require host-level routing to per-operator subprocesses or a
future per-call identity contract.

## Usage examples

Once connected, ask any MCP-aware agent:

```
# Write a decision fact
assert_fact(
  entity="decision:use-sqlite",
  relation="roadmap:status",
  value={"type":"string","v":"approved"},
  source="agent:cto",
  session_id="mcp:agent-01"
)

# Query all active project constraints
query_facts(entity="project:acme-platform", relation="roadmap:constraint")

# Recall context for a project question
recall(query="What is blocking the launch?", scope="local", token_budget=1000)

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
  See `Spec-02-Scopes-and-ACL` for the full scope semantics.
- `recall` returns `content` and `instructions` arrays as separate channels, plus
  `system_prompt_directive`. MCP hosts must keep those channels distinct and place
  the directive above recalled content instead of concatenating recalled data into
  higher-priority prompts.
- `assert_fact`, `query_facts`, `recall`, and `subscribe_scope` propagate a
  `Stigmem-Session` header. Pass `session_id` per tool call for
  conversation-specific attribution, or set `STIGMEM_SESSION_ID` for a stable
  process-level override.
- `assert_fact` accepts `write_mode="summarize_with_provenance"` plus
  `derived_from=[{"fact_id":"..."}]` for legitimate agent summaries derived
  from recalled facts.

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
