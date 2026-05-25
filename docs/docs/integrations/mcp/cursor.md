---
title: Cursor
sidebar_label: Cursor
audience: Integrator
---

# Stigmem in Cursor

**Validation tier:** Experimental.

Cursor can launch `stigmem-mcp` from an MCP config file. Host UI smoke evidence
is still pending, so this connector remains experimental.

## Install

```bash
npm install -g @eidetic-labs/stigmem-mcp
```

## Configure

```bash
stigmem mcp config cursor
stigmem mcp install cursor --write
```

The default config path is `~/.cursor/mcp.json`.

## Verify

```bash
stigmem mcp smoke cursor
```

Restart Cursor after changing MCP settings.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server listed but no tools | Confirm `stigmem-mcp` is on PATH for Cursor's process environment |
| Timeout on startup | Confirm the Stigmem node is running |
| Auth errors | Check `STIGMEM_API_KEY` |
