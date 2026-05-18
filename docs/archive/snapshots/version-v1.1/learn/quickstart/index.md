---
id: index
title: Getting Started
sidebar_label: Overview
---

# Getting Started

Stigmem is a structured, federated knowledge graph for AI agents. Each fact is an immutable **(entity, relation, value)** triple with provenance, confidence, scope, and a hybrid logical clock timestamp.

## Video walkthroughs

:::info Coming soon
Video walkthroughs for self-hosted node setup, federation, and MCP adapter usage are in production and will be linked here when published.
:::

## Quickest start — Docker (recommended)

No Python required. Install with a single command:

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem
docker compose up --build -d
```

Two federated nodes start on ports 8765 and 8766. See the [Installation page](./installation) for full options and the [Quickstart](./quickstart-tutorial) to verify federation end-to-end.

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

## Hosted offering

:::info Coming soon
A free-tier hosted stigmem node is on the roadmap. [Join the discussion](https://github.com/eidetic-labs/stigmem/discussions) to register interest and get notified at launch.
:::

## Two-node federation quickstart

To run two nodes and verify cross-node fact replication, see the [Quickstart](./quickstart-tutorial) guide. It takes under 10 minutes and requires only Docker.

## Explore interactively

Once the node is running, regenerate the interactive API reference:

```bash
cd stigmem/docs
npm run gen-api-docs
npm run start
```

Then open `http://localhost:3000/docs/api-reference` to try API calls directly from the docs.
