---
title: Querying Facts
sidebar_label: Querying Facts
audience: Integrator
---

# Querying Facts

**Audience:** Agent developers consuming Stigmem facts.

:::info Coming soon
Full guide content is planned for the next docs sprint.
:::

## Quick example

```bash
# All facts for a specific entity
curl -s 'http://localhost:8000/v1/facts?entity=user:alice' \
  -H 'X-API-Key: dev-key' | jq .facts

# Filter by entity + relation
curl -s 'http://localhost:8000/v1/facts?entity=user:alice&relation=memory:prefers' \
  -H 'X-API-Key: dev-key' | jq '.facts[0].value'

# Only high-confidence facts
curl -s 'http://localhost:8000/v1/facts?min_confidence=0.8' \
  -H 'X-API-Key: dev-key' | jq .
```

## Topics to be covered

- Filtering by entity, relation, source, scope (see spec §5.2)
- Cursor-based pagination via the `cursor` field
- Polling for new facts with the `after` HLC cursor
- Including contradicted and expired facts
- Scoped access (local vs company facts)

See the [API Reference](/docs/reference/api) for the full `GET /v1/facts` endpoint spec.
