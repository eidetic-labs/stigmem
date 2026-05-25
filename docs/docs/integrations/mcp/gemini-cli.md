---
title: Gemini CLI
sidebar_label: Gemini CLI
audience: Integrator
---

# Stigmem in Gemini CLI

**Validation tier:** Caveated.

Gemini CLI completed MCP tool execution in the 2026-05-24 host smoke, including
assert, query, recall, malformed-call handling, and fresh-session lifecycle.
Some final-response rendering paths emitted `INVALID_STREAM` after successful
tool calls, so support remains caveated until a clean host release is verified.

## Install

```bash
npm install -g @eidetic-labs/stigmem-mcp
```

## Configure

```bash
stigmem mcp config gemini-cli
stigmem mcp install gemini-cli --write
```

The default config path is `~/.gemini/settings.json`.

## Verify

```bash
stigmem mcp smoke gemini-cli
gemini mcp list
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `INVALID_STREAM` after tool calls | Treat as a host rendering caveat if the tool call itself succeeded |
| Server missing | Confirm Gemini sees the same config file changed by `stigmem mcp install` |
| Auth errors | Check `STIGMEM_API_KEY` |
