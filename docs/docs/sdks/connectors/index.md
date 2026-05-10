---
title: Connectors
sidebar_label: Overview
sidebar_position: 1
audience: Integrator
---

# Connectors

Install recipes and smoke tests for running the Stigmem MCP server inside popular
editors, agent CLIs, and non-MCP runtimes.

## MCP host connectors

These guides configure the existing MCP server (`stigmem/adapters/mcp/`) as a tool
provider inside each host. Build the server once, then register it in each host's
config.

| Guide | Host |
|-------|------|
| [Zed (experimental)](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/mcp-adapter) | Zed editor — `mcp_servers` block in `settings.json` |
| [Cursor](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/mcp-adapter) | Cursor editor — `.cursor/mcp.json` |
| [Codex CLI](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/mcp-adapter) | OpenAI Codex CLI — `~/.codex/config.yaml` |
| [Continue.dev](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/mcp-adapter) | Continue VS Code/JetBrains extension — `.continue/config.json` |

## Runtime adapters

These adapters translate Stigmem's tools into the native function-calling format of
non-MCP runtimes.

| Guide | Runtime |
|-------|---------|
| [Gemini](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/adapter-gemini) | Google Gemini — native `FunctionDeclaration` format |
| [Ollama / LiteLLM (experimental)](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/adapter-ollama-litellm) | OpenAI-compatible tool-use format for local models |

## Agent platform adapters

These adapters integrate Stigmem with agent orchestration platforms via their
native skill or hook surfaces (not MCP).

| Guide | Platform |
|-------|----------|
| [OpenClaw](./openclaw) | OpenClaw — ClawHub skill providing boot handshake, handoff, decision, and escalation surfaces |
| [Paperclip / Claude Code](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/adapter-paperclip) | Paperclip and Claude Code — MCP server registered in `.mcp.json` |

## Vault / note-taking adapters

These adapters sync Stigmem facts with local markdown vaults, enabling bidirectional
integration with note-taking tools.

| Guide | Tool |
|-------|------|
| [Obsidian Vault](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/adapter-obsidian) | CLI/daemon sync for Obsidian, Logseq, Dendron, and plain-folder markdown vaults |

## Memory federation adapters

These adapters bridge Stigmem with other memory systems to share knowledge across
boundaries.

| Guide | System |
|-------|--------|
| [Zep](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/adapter-zep) | Zep — mirror shared facts into per-user/session episodic memory |

## Shared prerequisites

All host connectors require a built MCP server binary:

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
# binary: dist/server.js
```

And a running Stigmem node:

```bash
cd stigmem/node
uv run uvicorn stigmem_node.main:app --port 8765
```

Set `STIGMEM_API_KEY` if your node has `STIGMEM_AUTH_REQUIRED=true`.
