---
id: cursor
title: Cursor
sidebar_label: Cursor
---

# Stigmem in Cursor

Connect the Stigmem MCP server to [Cursor](https://cursor.sh) so Cursor's AI
features can read and write Stigmem facts during sessions.

## Prerequisites

- Cursor ≥ 0.42 (MCP support)
- Node.js ≥ 18
- A running Stigmem node at `STIGMEM_URL`

## Step 1 — Build the MCP server

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
# produces: stigmem/adapters/mcp/dist/server.js
```

## Step 2 — Create `.cursor/mcp.json`

In your project root (or `~/.cursor/mcp.json` for a global config):

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

Replace `/absolute/path/to/stigmem` with the real path.
Omit `STIGMEM_API_KEY` if your node runs without auth.

## Step 3 — Reload Cursor

1. Open the Command Palette (`Cmd+Shift+P`).
2. Run **MCP: Reload Servers** (or restart Cursor).
3. Open **Settings → MCP** and confirm `stigmem` shows a green status.

## Smoke test

```bash
bash stigmem/adapters/mcp/tests/smoke.sh
```

## npx alternative

If you prefer not to build locally, you can run the server via npx once the package
is published to npm:

```json
{
  "mcpServers": {
    "stigmem": {
      "command": "npx",
      "args": ["-y", "stigmem-mcp"],
      "env": {
        "STIGMEM_URL": "http://localhost:8765",
        "STIGMEM_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Server listed but no tools | Ensure `dist/server.js` exists — run `pnpm build` |
| `Cannot find module` | Confirm `node_modules` are installed: `pnpm install` |
| Timeout on startup | Check that the Stigmem node is running (`curl http://localhost:8765/healthz`) |

## See also

- [Zed](./zed) — similar MCP config for Zed
- [Authentication](../authentication) — API key setup
