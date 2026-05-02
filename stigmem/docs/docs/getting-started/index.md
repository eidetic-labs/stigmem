---
id: index
title: Getting Started
sidebar_label: Overview
---

# Getting Started

Stigmem is a structured, federated knowledge graph for AI agents. Each fact is an immutable **(entity, relation, value)** triple with provenance, confidence, scope, and a hybrid logical clock timestamp.

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.11 |
| SQLite | ≥ 3.37 |
| uv (recommended) | latest |

## Run the reference node

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
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity": "user:alice",
    "relation": "memory:prefers",
    "value": "dark mode",
    "source": "agent:settings",
    "confidence": 1.0,
    "scope": "local"
  }' | jq .
```

The response includes an `id`, `hlc` (hybrid logical clock tick), and `timestamp`.

## Query it back

```bash
curl -s 'http://localhost:8000/v1/facts?entity=user:alice&relation=memory:prefers' \
  -H 'X-API-Key: dev-key' | jq .facts
```

## Explore interactively

Once the node is running, regenerate the interactive API reference:

```bash
cd stigmem/docs
npm run gen-api-docs
npm run start
```

Then open `http://localhost:3000/docs/api-reference` to try API calls directly from the docs.

:::info Coming soon
Step-by-step installation guide, environment variable reference, and Docker quickstart are planned for the next docs sprint.
:::
