---
title: Zed
sidebar_label: Zed
audience: Integrator
---

# Stigmem in Zed

**Validation tier:** Experimental.

Zed can launch `stigmem-mcp` from its settings file. Host UI smoke evidence is
still pending, so this connector remains experimental.

## Install

```bash
npm install -g stigmem-mcp
```

## Configure

```bash
stigmem mcp config zed
stigmem mcp install zed --write
```

The default config path is `~/.config/zed/settings.json`.

## Verify

```bash
stigmem mcp smoke zed
```

Restart Zed after changing settings.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `stigmem` not listed | Confirm the `mcp_servers` block is present in settings |
| `STIGMEM_URL` missing | Confirm the generated env block was written |
| Auth errors | Check `STIGMEM_API_KEY` |
