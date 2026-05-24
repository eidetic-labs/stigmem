---
title: Zed
sidebar_label: Zed
audience: Integrator
---

# Stigmem in Zed

Connect the Stigmem MCP server to the [Zed editor](https://zed.dev) so AI features
in Zed (Agent Panel, inline assists) can read and write Stigmem facts.

## Prerequisites

- Zed ≥ 0.150 (MCP support in the Agent Panel)
- Node.js ≥ 18
- A running Stigmem node at `STIGMEM_URL`

## Step 1 — Build the MCP server

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
# produces: stigmem/adapters/mcp/dist/server.js
```

## Step 2 — Add to Zed settings

Open **Zed → Settings** (`Cmd+,` on macOS) and add an `mcp_servers` block:

```jsonc
{
  "mcp_servers": {
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

Replace `/absolute/path/to/stigmem` with the real path on your machine.
`STIGMEM_API_KEY` can be omitted if your node runs with `STIGMEM_AUTH_REQUIRED=false`.

## Step 3 — Reload and verify

1. Reload Zed (close and reopen, or use the Command Palette → **Reload**).
2. Open the Agent Panel (`Cmd+Shift+A`).
3. Confirm `stigmem` appears in the tools list (click the spanner icon).

## Smoke test

Run this from the repo root to verify end-to-end connectivity independent of the editor:

```bash
bash stigmem/adapters/mcp/tests/smoke.sh
```

The script starts the MCP server, sends `initialize` + `tools/list`, confirms
all six Stigmem tools are present, then validates `assert_fact`, `query_facts`,
`recall`, `lint_scope`, and session-aware calls against the configured node.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `stigmem` not listed in tools | Check the `args` path — must be absolute |
| `STIGMEM_URL is required` in server logs | The `env` block is missing or malformed |
| Auth error from Stigmem node | Set `STIGMEM_API_KEY` or disable auth on the node |
| `node: command not found` | Change `"command"` to the absolute path: `"/usr/local/bin/node"` |

## See also

- [MCP server reference](../../reference/architecture) — tool schema and protocol notes
- [Authentication](../../security/authentication) — API key and OIDC setup
