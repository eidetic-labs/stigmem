---
title: MCP integrations
sidebar_label: Overview
audience: Integrator
---

# MCP integrations

Stigmem ships `stigmem-mcp`, a stdio MCP server that lets MCP-aware editors
read from and write to a Stigmem node. The adapter exposes six tools:
`assert_fact`, `query_facts`, `recall`, `resolve_contradiction`,
`subscribe_scope`, and `lint_scope`.

## Install

```bash
npm install -g stigmem-mcp
# or run without a global install:
npx -y stigmem-mcp@0.9.0-alpha.9
```

## Quick start

```bash
stigmem mcp doctor
stigmem mcp detect
stigmem mcp config codex-cli
stigmem mcp install codex-cli
stigmem mcp install codex-cli --write
stigmem mcp smoke codex-cli
```

`stigmem mcp install` defaults to a dry run. Passing `--write` creates a
timestamped backup before changing an existing editor config.
`stigmem mcp config` prints metadata and the connector guide link only; use
the install dry run to preview the planned Stigmem server entry with the
credential field omitted from console output.

## Supported editors

| Editor | Validation tier | Guide |
|---|---|---|
| Codex CLI | Validated | [Codex CLI](./codex-cli.md) |
| Claude Code | Validated | [Claude Code](./claude-code.md) |
| Gemini CLI | Caveated | [Gemini CLI](./gemini-cli.md) |
| Continue.dev | Experimental | [Continue.dev](./continue-dev.md) |
| Cursor | Experimental | [Cursor](./cursor.md) |
| Zed | Experimental | [Zed](./zed.md) |

Validation tiers:

- **Validated:** host UI smoke evidence is on file.
- **Caveated:** tool execution passed with a documented host-side caveat.
- **Experimental:** connector guide exists; host UI smoke evidence is pending.

## Trust model

The MCP adapter is an editor-launched subprocess. The editor authorizes process
launch, then `STIGMEM_URL` and `STIGMEM_API_KEY` determine what the subprocess
can read and write on the node. Treat the subprocess like any other local tool
that can call the node API with that key.

Use one key per operator or trust boundary. Do not reuse the same MCP config
across mutually untrusted workspaces.

## Troubleshooting

| Symptom | Check |
|---|---|
| `stigmem-mcp` not found | Run `npm install -g stigmem-mcp` or use the `npx` snippet in your editor config |
| Auth errors | Confirm `STIGMEM_API_KEY` matches a valid node key |
| Connection refused | Confirm the node is reachable at `STIGMEM_URL` |
| Tools missing in the editor | Run `stigmem mcp status` and restart the editor after config changes |

See also: [MCP adapter security](https://github.com/eidetic-labs/stigmem/blob/main/features/mcp-adapter/security.md).
