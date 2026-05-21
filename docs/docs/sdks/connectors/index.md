---
title: Connectors
sidebar_label: Overview
sidebar_position: 1
audience: Integrator
---

# Connectors

<p className="stigmem-meta"><span>2 min read</span><span>Integrator</span><span>Adapter index</span></p>

<div className="stigmem-lead">

**What this section covers**

Install recipes and smoke tests for running the Stigmem MCP server
inside popular editors, agent CLIs, and non-MCP runtimes.

</div>

## MCP host connectors

These guides configure the existing MCP server (`stigmem/adapters/mcp/`) as a tool provider inside each host. Build the server once, then register it in each host's config. The canonical feature record is [`features/mcp-adapter`](https://github.com/eidetic-labs/stigmem/tree/main/features/mcp-adapter).

<div className="stigmem-fields">

<div>
<dt>Host</dt>
<dt><span className="stigmem-fields__type">Config location</span></dt>
<dd>Guide</dd>
</div>

<div>
<dt>Zed (experimental)</dt>
<dt><span className="stigmem-fields__type"><code>mcp_servers</code> in <code>settings.json</code></span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/features/mcp-adapter">features/mcp-adapter</a></dd>
</div>

<div>
<dt>Cursor</dt>
<dt><span className="stigmem-fields__type"><code>.cursor/mcp.json</code></span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/features/mcp-adapter">features/mcp-adapter</a></dd>
</div>

<div>
<dt>Codex CLI</dt>
<dt><span className="stigmem-fields__type"><code>~/.codex/config.yaml</code></span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/features/mcp-adapter">features/mcp-adapter</a></dd>
</div>

<div>
<dt>Continue.dev</dt>
<dt><span className="stigmem-fields__type"><code>.continue/config.json</code></span></dt>
<dd>Continue VS Code/JetBrains extension.</dd>
</div>

</div>

## Runtime adapters

These adapters translate Stigmem's tools into the native function-calling format of non-MCP runtimes.

<div className="stigmem-fields">

<div>
<dt>Runtime</dt>
<dt><span className="stigmem-fields__type">Format</span></dt>
<dd>Guide</dd>
</div>

<div>
<dt>Gemini</dt>
<dt><span className="stigmem-fields__type">native <code>FunctionDeclaration</code></span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/features/gemini-adapter">features/gemini-adapter</a></dd>
</div>

<div>
<dt>Ollama / LiteLLM</dt>
<dt><span className="stigmem-fields__type">OpenAI-compatible tool-use</span></dt>
<dd>For local models. <a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/adapter-ollama-litellm">experimental/adapter-ollama-litellm</a></dd>
</div>

</div>

## Agent platform adapters

<div className="stigmem-fields">

<div>
<dt>Platform</dt>
<dt><span className="stigmem-fields__type">Integration</span></dt>
<dd>Guide</dd>
</div>

<div>
<dt>OpenClaw</dt>
<dt><span className="stigmem-fields__type">ClawHub skill</span></dt>
<dd>Boot handshake, handoff, decision, and escalation surfaces. <a href="./openclaw">OpenClaw guide</a>.</dd>
</div>

<div>
<dt>Paperclip / Claude Code</dt>
<dt><span className="stigmem-fields__type">MCP server in <code>.mcp.json</code></span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/adapter-paperclip">experimental/adapter-paperclip</a></dd>
</div>

</div>

## Vault / note-taking adapters

<div className="stigmem-fields">

<div>
<dt>Tool</dt>
<dt><span className="stigmem-fields__type">Sync mode</span></dt>
<dd>Guide</dd>
</div>

<div>
<dt>Obsidian / Logseq / Dendron</dt>
<dt><span className="stigmem-fields__type">CLI/daemon</span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/features/obsidian-adapter">features/obsidian-adapter</a></dd>
</div>

</div>

## Memory federation adapters

<div className="stigmem-fields">

<div>
<dt>System</dt>
<dt><span className="stigmem-fields__type">Bridge</span></dt>
<dd>Guide</dd>
</div>

<div>
<dt>Zep</dt>
<dt><span className="stigmem-fields__type">episodic memory mirror</span></dt>
<dd>Mirror shared facts into per-user/session episodic memory. <a href="https://github.com/eidetic-labs/stigmem/tree/main/features/zep-adapter">features/zep-adapter</a></dd>
</div>

</div>

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

<div className="stigmem-keypoint">

**Set `STIGMEM_API_KEY` if your node has `STIGMEM_AUTH_REQUIRED=true`.**

</div>
