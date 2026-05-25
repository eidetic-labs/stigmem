---
title: Codex CLI
sidebar_label: Codex CLI
audience: Integrator
---

# Stigmem in Codex CLI

**Validation tier:** Validated.

Codex CLI can launch `stigmem-mcp` as a stdio MCP server so coding sessions can
read and write Stigmem facts.

## Install

```bash
npm install -g @eidetic-labs/stigmem-mcp
```

## Configure

Print the config snippet:

```bash
stigmem mcp config codex-cli
```

Apply it with backup handling:

```bash
stigmem mcp install codex-cli --write
```

Codex reads the global config from `~/.codex/config.toml`.

## Verify

```bash
stigmem mcp smoke codex-cli
codex mcp list
```

The host should expose `assert_fact`, `query_facts`, `recall`,
`resolve_contradiction`, `subscribe_scope`, and `lint_scope`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tools not listed | Confirm `~/.codex/config.toml` references `stigmem-mcp`, then restart Codex |
| Auth errors | Check `STIGMEM_API_KEY` |
| Node unavailable | Check `STIGMEM_URL` and the node `/healthz` endpoint |
