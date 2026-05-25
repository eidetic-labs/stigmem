---
title: Continue.dev
sidebar_label: Continue.dev
audience: Integrator
---

# Stigmem in Continue.dev

**Validation tier:** Experimental.

Continue.dev can launch `stigmem-mcp` from its MCP server list. Host UI smoke
evidence is still pending, so this connector remains experimental.

## Install

```bash
npm install -g @eidetic-labs/stigmem-mcp
```

## Configure

```bash
stigmem mcp config continue-dev
stigmem mcp install continue-dev --write
```

The default config path is `~/.continue/config.json`.

## Verify

```bash
stigmem mcp smoke continue-dev
```

Reload Continue after changing the config.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Servers not loading | Confirm Continue MCP support is enabled in your installed version |
| Tools missing | Refresh MCP servers or restart the host |
| Auth errors | Check `STIGMEM_API_KEY` |
