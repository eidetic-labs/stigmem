---
id: continue-dev
title: Continue.dev
sidebar_label: Continue.dev
audience: Integrator
---

# Stigmem in Continue.dev

Connect the Stigmem MCP server to
[Continue](https://continue.dev) (VS Code and JetBrains extension) so Continue's
AI assistant can read and write Stigmem facts.

## Prerequisites

- Continue extension ≥ 0.9.235 (MCP support)
- Node.js ≥ 18
- A running Stigmem node at `STIGMEM_URL`

## Step 1 — Build the MCP server

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
# produces: stigmem/adapters/mcp/dist/server.js
```

## Step 2 — Add to Continue config

Edit `~/.continue/config.json` (global) or `.continue/config.json` in the project root:

```json
{
  "mcpServers": [
    {
      "name": "stigmem",
      "command": "node",
      "args": ["/absolute/path/to/stigmem/adapters/mcp/dist/server.js"],
      "env": {
        "STIGMEM_URL": "http://localhost:8765",
        "STIGMEM_API_KEY": "sk-your-key-here"
      }
    }
  ]
}
```

:::note
Continue uses an **array** of MCP servers (`"mcpServers": [...]`) rather than a
keyed object. The `"name"` field is the display label shown in the UI.
:::

Replace `/absolute/path/to/stigmem` with the real path.
Omit `STIGMEM_API_KEY` if auth is disabled on your node.

## Step 3 — Reload and verify

1. Open the Command Palette in VS Code (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Run **Continue: Refresh MCP Servers**.
3. In the Continue sidebar, confirm `stigmem` tools appear (click the tools icon).

## Smoke test

```bash
bash stigmem/adapters/mcp/tests/smoke.sh
```

## Using Stigmem in Continue chat

Once connected, you can invoke Stigmem tools directly in the chat:

```
@stigmem assert_fact entity="project:my-app" relation="roadmap:status" value={"type":"string","v":"in_progress"} source="agent:me"
```

Or ask Continue to use the tools in natural language:

```
Check Stigmem for any active constraints on this project.
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Servers not loading | Check Continue version ≥ 0.9.235 |
| `"name"` field missing | `name` is required in Continue's array format |
| Permission denied | Ensure `dist/server.js` is executable or use `node` explicitly |

## See also

- [Zed](./zed) — Zed config (object format instead of array)
- [Cursor](./cursor) — Cursor `.cursor/mcp.json` format
