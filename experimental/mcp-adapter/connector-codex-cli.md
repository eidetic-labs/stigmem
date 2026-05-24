---
title: Codex CLI
sidebar_label: Codex CLI
audience: Integrator
---

# Stigmem in Codex CLI

Connect the Stigmem MCP server to the
[OpenAI Codex CLI](https://github.com/openai/codex) so Codex agents can
read and write Stigmem facts during coding sessions.

## Prerequisites

- Codex CLI installed: `npm install -g @openai/codex`
- Node.js ≥ 18
- A running Stigmem node at `STIGMEM_URL`

## Step 1 — Build the MCP server

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
# produces: stigmem/adapters/mcp/dist/server.js
```

## Step 2 — Add to Codex config

Edit `~/.codex/config.yaml` (create it if it doesn't exist):

```yaml
mcpServers:
  stigmem:
    command: node
    args:
      - /absolute/path/to/stigmem/adapters/mcp/dist/server.js
    env:
      STIGMEM_URL: "http://localhost:8765"
      STIGMEM_API_KEY: "sk-your-key-here"
```

Replace `/absolute/path/to/stigmem` with the real path.
Omit `STIGMEM_API_KEY` if auth is disabled on your node.

## Step 3 — Verify

Start a Codex session and confirm Stigmem tools are available:

```bash
codex --tools
# → Should list: assert_fact, query_facts, recall, resolve_contradiction, subscribe_scope, lint_scope
```

## Smoke test

```bash
bash stigmem/adapters/mcp/tests/smoke.sh
```

The smoke starts the MCP server over stdio and validates initialize, six-tool
discovery, `assert_fact`, `query_facts`, `recall`, `lint_scope`, and
session-aware calls against the configured node.

## Per-project config

You can also place the config in the project root as `.codex/config.yaml`:

```yaml
mcpServers:
  stigmem:
    command: node
    args:
      - ./stigmem/adapters/mcp/dist/server.js
    env:
      STIGMEM_URL: "http://localhost:8765"
```

Relative paths in `args` are resolved from the project root when Codex is run
from that directory.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Tools not listed | Verify config path: `~/.codex/config.yaml` or `.codex/config.yaml` |
| `spawn node ENOENT` | Use the absolute path to node: `which node` |
| Auth errors | Check `STIGMEM_API_KEY` matches the key created on the node |

## See also

- [Claude Code](../../security/authentication) — Claude Code uses `.claude/mcp_servers.json` (same server, different config location)
- [Cursor](./cursor) — Cursor config reference
