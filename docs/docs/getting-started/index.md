---
id: index
title: Getting Started
sidebar_label: Overview
---

# Getting Started

Stigmem is a structured, federated knowledge graph for AI agents. Each fact is an immutable **(entity, relation, value)** triple with provenance, confidence, scope, and a hybrid logical clock timestamp.

## Video walkthroughs

Prefer video? Three short walkthroughs cover the main paths — each under 10 minutes.

| # | Title | What you'll learn |
|---|-------|-------------------|
| 1 | [Self-hosted node setup](#) | Install, configure, and start a stigmem node with Docker Compose |
| 2 | [Federation walkthrough](#) | Connect two nodes and watch facts replicate automatically |
| 3 | [MCP adapter usage](#) | Wire stigmem into Claude Code or any MCP-compatible agent |

<!-- TODO: replace # hrefs above with published video URLs once recorded and uploaded -->

## Quickest start — Docker (recommended)

No Python required. Install with a single command:

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
docker compose up --build -d
```

Two federated nodes start on ports 8765 and 8766. See the [Installation page](./installation) for full options and the [Quickstart](./quickstart) to verify federation end-to-end.

## Development (Python)

For hacking on the source or running without Docker:

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.11 |
| SQLite | ≥ 3.37 |
| uv (recommended) | latest |

```bash
cd stigmem/node
uv run python -m stigmem_node
```

The node starts on `http://localhost:8000`.

- Interactive Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- Well-known metadata (spec §5.3): `http://localhost:8000/.well-known/stigmem`

## Assert your first fact

```bash
curl -s -X POST http://localhost:8000/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-key' \
  -d '{
    "entity": "user:alice",
    "relation": "memory:prefers",
    "value": {"type": "string", "v": "dark mode"},
    "source": "agent:settings",
    "confidence": 1.0,
    "scope": "local"
  }' | jq .
```

The response includes an `id`, `hlc` (hybrid logical clock tick), and `timestamp`.

## Query it back

```bash
curl -s 'http://localhost:8000/v1/facts?entity=user:alice&relation=memory:prefers' \
  -H 'Authorization: Bearer dev-key' | jq .facts
```

## Two-node federation quickstart

To run two nodes and verify cross-node fact replication, see the [Quickstart](./quickstart) guide. It takes under 10 minutes and requires only Docker.

## Video walkthroughs

| Video | Duration | What you'll learn |
|-------|----------|-------------------|
| [Self-hosted node setup](#) <!-- TODO: replace with upload URL --> | ~9 min | Install, start, assert your first fact, query, teardown |
| [Federation walkthrough](#) <!-- TODO: replace with upload URL --> | ~9 min | Connect two nodes, peer handshake, fact replication, scope enforcement, conflict resolution |
| [MCP adapter usage](#) <!-- TODO: replace with upload URL --> | ~9 min | Build and configure the adapter, demo all five MCP tools |

## Explore interactively

Once the node is running, regenerate the interactive API reference:

```bash
cd stigmem/docs
npm run gen-api-docs
npm run start
```

Then open `http://localhost:3000/docs/api-reference` to try API calls directly from the docs.
