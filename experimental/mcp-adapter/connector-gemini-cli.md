---
title: Gemini CLI
sidebar_label: Gemini CLI
audience: Integrator
---

# Stigmem in Gemini CLI

Connect the Stigmem MCP server to Gemini CLI so Gemini agents can call Stigmem
tools through stdio MCP.

## Validation state

Gemini CLI `0.43.0` completed MCP tool execution in the `2026-05-24` host
smoke: `assert_fact`, `query_facts`, `recall`, malformed-call error display,
and fresh-session lifecycle all succeeded against a loopback node. The host also
emitted `INVALID_STREAM` on some final-response/rendering paths after successful
tool calls. Treat Gemini CLI support as caveated until a future Gemini CLI
version produces clean final output.

## Prerequisites

- Gemini CLI installed.
- Node.js >= 18.
- A running Stigmem node at `STIGMEM_URL`.
- The MCP server built:

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
```

## Project-scoped setup

Use project scope when testing so the server entry is local to the checkout:

```bash
gemini mcp add \
  --scope project \
  --trust \
  --env STIGMEM_URL=http://localhost:8765 \
  stigmem \
  node /absolute/path/to/stigmem/adapters/mcp/dist/server.js
```

If your local node requires auth, add:

```bash
--env STIGMEM_API_KEY=sk-your-key-here
```

Verify the server:

```bash
gemini mcp list
```

The `stigmem` server should appear as connected.

## Smoke prompt

Run a bounded prompt that uses only the Stigmem MCP server:

```bash
gemini \
  --skip-trust \
  --allowed-mcp-server-names stigmem \
  --prompt "Use only the configured stigmem MCP tools. Assert a local fact, query it back, recall it, and report whether content and instructions stayed separate."
```

Do not use broad auto-approval modes for publication smoke unless the maintainer
explicitly approves that risk.

## Cleanup

Remove the project-scoped server entry when the smoke is finished:

```bash
gemini mcp remove stigmem
```

or delete the temporary project `.gemini/settings.json` if it was created only
for the smoke run.

