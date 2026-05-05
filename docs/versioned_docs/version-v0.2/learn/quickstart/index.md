---
id: index
title: Getting Started (v0.2)
sidebar_label: Overview
---

# Getting Started

:::note
This is the **v0.2** documentation — the first public draft of the Stigmem specification (seeking design-partner feedback). For the current implementation see the [v0.5 docs](/docs/v0.2/learn/quickstart).
:::

## What changed in v0.2

v0.2 introduced the `text` FactValue type, the reification pattern (N-ary relationships via `loom:rel:` prefix — renamed to `stigmem:rel:` in v0.5), and the `valid_until` expiry field.

## Quick start (v0.2 wire format)

```bash
curl -X POST http://localhost:8000/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity": "user:alice",
    "relation": "memory:prefers",
    "value": "dark mode",
    "source": "agent:settings",
    "confidence": 1.0,
    "scope": "local"
  }'
```

The v0.2 wire format does not include the `hlc` field (added in v0.5).
