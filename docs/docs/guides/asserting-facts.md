---
id: asserting-facts
title: Asserting Facts
sidebar_label: Asserting Facts
---

# Asserting Facts

**Audience:** Node operators and agent developers using the Stigmem REST API.

:::info Coming soon
Full guide content is planned for the next docs sprint.
:::

## Quick example

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

## Topics to be covered

- Creating a new fact
- Updating a fact (asserting a new fact with the same entity/relation — see spec §3)
- Retracting a fact (`confidence: 0`)
- Reification for N-ary relationships (`stigmem:rel:<uuid>` — see spec §2.3)
- Using `valid_until` for ephemeral facts

See the [API Reference](/docs/api-reference) for the full `POST /v1/facts` endpoint spec.
