---
title: Claude Code
sidebar_label: Claude Code
audience: Integrator
---

# Stigmem in Claude Code

**Validation tier:** Validated.

Claude Code can launch `stigmem-mcp` as a stdio MCP server backed by your
Stigmem node.

## Install

```bash
npm install -g @eidetic-labs/stigmem-mcp
```

## Configure

```bash
stigmem mcp config claude-code
stigmem mcp install claude-code --write
```

The default config path is `~/.claude/mcp_servers.json`.

## Verify

```bash
stigmem mcp smoke claude-code
```

Restart Claude Code after changing the config.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server missing | Confirm `~/.claude/mcp_servers.json` contains the `stigmem` server |
| Command not found | Install `stigmem-mcp` globally or use an absolute command path |
| Auth errors | Rotate or replace `STIGMEM_API_KEY` on the node |
