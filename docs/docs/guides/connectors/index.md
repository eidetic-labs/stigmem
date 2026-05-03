---
id: connectors-index
title: Connectors
sidebar_label: Overview
sidebar_position: 1
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
| [Zed](./zed) | Zed editor — `mcp_servers` block in `settings.json` |
| [Cursor](./cursor) | Cursor editor — `.cursor/mcp.json` |
| [Codex CLI](./codex-cli) | OpenAI Codex CLI — `~/.codex/config.yaml` |
| [Continue.dev](./continue-dev) | Continue VS Code/JetBrains extension — `.continue/config.json` |

## Runtime adapters

These adapters translate Stigmem's tools into the native function-calling format of
non-MCP runtimes.

| Guide | Runtime |
|-------|---------|
| [Gemini](./gemini) | Google Gemini — native `FunctionDeclaration` format |
| [Ollama / LiteLLM](./ollama-litellm) | OpenAI-compatible tool-use format for local models |

## Memory federation adapters

These adapters bridge Stigmem with other memory systems to share knowledge across
boundaries.

| Guide | System |
|-------|--------|
| [Zep](./zep) | Zep — mirror shared facts into per-user/session episodic memory |

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
