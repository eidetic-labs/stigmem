---
title: Paperclip / Claude Code
sidebar_label: Paperclip / Claude Code
audience: Integrator
---

# Stigmem in Paperclip and Claude Code

Connect the Stigmem MCP server to [Paperclip](https://paperclip.ing) or the
[Claude Code CLI](https://claude.ai/code) so agents can read and write Stigmem
facts during heartbeat runs.

**Audience:** Agent developers and node operators deploying Stigmem as a persistent
knowledge store for Paperclip-managed agents.

## How it works

The Stigmem MCP server (`adapters/mcp/`) exposes Stigmem's REST API as MCP tools.
Claude Code and the Paperclip harness both speak MCP via `stdio`, so the server
acts as a bridge: your agent calls a tool, the MCP server translates it into a
Stigmem HTTP request, and the result comes back as structured JSON.

## Prerequisites

- A running Stigmem node (see [persistent service setup](../../get-started/installation#running-as-a-persistent-service-macos) or Docker)
- Node.js ≥ 18
- The MCP server built:

  ```bash
  cd stigmem/adapters/mcp
  pnpm install
  pnpm build
  # produces: stigmem/adapters/mcp/dist/server.js
  ```

## Configuring `.mcp.json`

Place (or merge) the following block in `.mcp.json` at your project root — Claude
Code and the Paperclip harness both pick it up automatically:

```json
{
  "mcpServers": {
    "stigmem": {
      "command": "node",
      "args": ["/absolute/path/to/stigmem/adapters/mcp/dist/server.js"],
      "env": {
        "STIGMEM_URL": "http://localhost:8765",
        "STIGMEM_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

Replace the `args` path with the real absolute path to `dist/server.js`.
Omit `STIGMEM_API_KEY` if your node runs without auth (the default for local dev).

:::tip Keep the node running
Use `bash scripts/service-install.sh` to register stigmem as a macOS LaunchAgent
that starts at login and restarts on crash. See the
[installation guide](../../get-started/installation#running-as-a-persistent-service-macos).
:::

## Available tools

The MCP server exposes five tools:

| Tool | Purpose |
|------|---------|
| `assert_fact` | Write a typed fact to the Stigmem node |
| `query_facts` | Query facts by entity, relation, scope, or confidence |
| `resolve_contradiction` | Resolve a detected conflict between two facts |
| `subscribe_scope` | Poll for recent facts in a scope (cursor-paginated) |
| `lint_scope` | Sweep a scope for health issues: contradictions, stale facts, orphans, broken refs |

### `assert_fact`

```json
{
  "entity":     "agent:my-agent",
  "relation":   "acme:goal_state",
  "value":      {"type": "string", "v": "PROJ-42: writing documentation"},
  "source":     "agent:my-agent",
  "confidence": 1.0,
  "scope":      "company"
}
```

The `value` field is a typed object — see [Asserting Facts](../guides/asserting-facts#factvalue-schema) for the full schema.

### `query_facts`

```json
{
  "entity":   "agent:my-agent",
  "relation": "acme:goal_state",
  "scope":    "company",
  "limit":    10
}
```

Returns a page of facts with a `cursor` for pagination.

### `resolve_contradiction`

```json
{
  "conflict_id":     "stigmem:conflict:<uuid>",
  "winning_fact_id": "<fact-id>",
  "resolution_note": "Keeping the more recent assertion"
}
```

Find conflicts with `query_facts` using `"include_contradicted": true`.

### `subscribe_scope`

```json
{
  "scope":  "company",
  "cursor": null,
  "limit":  50
}
```

Returns `facts`, `cursor`, and `has_more`. Pass the returned `cursor` on the next
call to follow new facts as they arrive.

## Heartbeat fact-assertion pattern

Agents should assert a standard set of facts each heartbeat run to give any
observer a live view of agent liveness and intent.

### Mandatory (every heartbeat)

Call `assert_fact` twice at the start of each run:

**`last_heartbeat`** — timestamp of this run:

```json
{
  "entity":     "agent:my-agent",
  "relation":   "acme:last_heartbeat",
  "value":      {"type": "datetime", "v": "2026-05-03T14:00:00Z"},
  "source":     "agent:my-agent",
  "confidence": 1.0,
  "scope":      "company"
}
```

**`goal_state`** — what the agent is currently working on:

```json
{
  "entity":     "agent:my-agent",
  "relation":   "acme:goal_state",
  "value":      {"type": "string", "v": "PROJ-42: writing documentation"},
  "source":     "agent:my-agent",
  "confidence": 1.0,
  "scope":      "company"
}
```

### Conditional

Assert these only when the situation applies:

**`blocked_by`** — when the agent cannot proceed:

```json
{
  "entity":     "agent:my-agent",
  "relation":   "acme:blocked_by",
  "value":      {"type": "ref", "v": "issue:PROJ-99"},
  "source":     "agent:my-agent",
  "confidence": 1.0,
  "scope":      "company"
}
```

**`decision`** — a significant decision made this heartbeat; use `valid_until` so
it expires and doesn't linger in the graph:

```json
{
  "entity":      "agent:my-agent",
  "relation":    "acme:decision",
  "value":       {"type": "string", "v": "Deferred API guide to child issue PROJ-55"},
  "source":      "agent:my-agent",
  "confidence":  1.0,
  "scope":       "company",
  "valid_until": "2026-05-03T23:59:59Z"
}
```

**`completed`** — asserted when a task is finished:

```json
{
  "entity":     "issue:PROJ-42",
  "relation":   "acme:completed",
  "value":      {"type": "boolean", "v": true},
  "source":     "agent:my-agent",
  "confidence": 1.0,
  "scope":      "company"
}
```

:::note Relation namespacing
Always prefix relations with a namespace (`acme:`, `memory:`, etc.). Bare relation
names such as `goal_state` are accepted but emit a server warning and risk
collisions. See [Asserting Facts](../guides/asserting-facts#relation-naming-convention).
:::

## Smoke test

```bash
bash adapters/mcp/tests/smoke.sh
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Server not listed in Claude Code | Check `.mcp.json` path; run `node adapters/mcp/dist/server.js` manually to see startup errors |
| `STIGMEM_URL is required` | Set `STIGMEM_URL` in the `env` block of `.mcp.json` |
| `Connection refused` | Stigmem node is not running — start it with `bash scripts/service-install.sh` |
| Tools timeout | Run `curl http://localhost:8765/healthz` to confirm the node is healthy |

## See also

- [Installation — persistent service](../../get-started/installation#running-as-a-persistent-service-macos)
- [Asserting Facts](../guides/asserting-facts) — FactValue schema and relation naming
- [Cursor](./cursor) — similar MCP config for Cursor editor
- [Authentication](../security/authentication) — API key setup
