# Stigmem MCP — Zed Integration

Quick-reference for wiring the Stigmem MCP server into [Zed](https://zed.dev) (≥ 0.150).
For the full narrative guide see `stigmem/docs/docs/guides/connectors/zed.md`.

## Prerequisites

- Zed ≥ 0.150
- Node.js ≥ 18 on PATH
- Stigmem node running: `cd stigmem/node && stigmem-node`
- MCP adapter built: `cd stigmem/adapters/mcp && pnpm install && pnpm build`

## Zed settings.json snippet

Open **Zed → Settings** (`Cmd+,`) and add:

```jsonc
{
  "mcp_servers": {
    "stigmem": {
      "command": "node",
      "args": ["/absolute/path/to/stigmem/adapters/mcp/dist/server.js"],
      "env": {
        "STIGMEM_URL": "http://localhost:8765"
      }
    }
  }
}
```

Replace `/absolute/path/to/stigmem` with the real path. Reload Zed after saving.

### With auth enabled (`STIGMEM_AUTH_REQUIRED=true`)

Add `STIGMEM_API_KEY` to the `env` block:

```jsonc
"env": {
  "STIGMEM_URL": "http://localhost:8765",
  "STIGMEM_API_KEY": "sk-your-key-here"
}
```

## Environment variable reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `STIGMEM_URL` | yes | — | Base URL of the Stigmem node |
| `STIGMEM_API_KEY` | no | — | API key (only when node runs with `STIGMEM_AUTH_REQUIRED=true`) |
| `STIGMEM_SESSION_ID` | no | generated per process | Stable session id propagated on session-aware read and write calls |
| `STIGMEM_POLL_LIMIT` | no | `50` | Max facts per `subscribe_scope` call (1–500) |

## Smoke test

Verifies the full assert → query → recall → lint path through the MCP protocol before opening Zed:

```bash
bash stigmem/adapters/mcp/tests/smoke.sh
```

The script (source: `tests/smoke.sh`) does:
1. Starts the MCP server over stdio
2. MCP `initialize` handshake
3. `tools/list` — confirms all 6 tools are present
4. `tools/call assert_fact` — writes a test fact to the node
5. `tools/call query_facts` — reads it back and asserts the value
6. `tools/call recall` — confirms recalled content stays channel-separated
7. `tools/call lint_scope` — runs a read-only live lint sweep

Exits 0 on success. Requires a running Stigmem node at `STIGMEM_URL`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `stigmem` not listed in Zed tools | `args` path must be absolute — check it exists |
| `STIGMEM_URL is required` in Zed output | `env` block is missing or outside `mcp_servers` |
| `connect ECONNREFUSED` | Stigmem node not running — start with `stigmem-node` |
| 401 Unauthorized | Add `STIGMEM_API_KEY` to the `env` block |
| `node: command not found` | Use absolute path: `"command": "/usr/local/bin/node"` |
