---
id: conflict-resolution
title: Conflict Resolution
sidebar_label: Conflict Resolution
---

# Conflict Resolution

**Audience:** Agent developers and node operators managing contradictory facts.

:::info Coming soon
Full guide content is planned for the next docs sprint.
:::

## What is a conflict?

A conflict occurs when two facts share the same (entity, relation, scope) tuple but carry different values. Stigmem stores both facts and creates a `ConflictRecord` — it never silently overwrites. See spec §3 and §5.9.

## List open conflicts

```bash
curl -s 'http://localhost:8000/v1/conflicts?status=open' \
  -H 'X-API-Key: dev-key' | jq .
```

## Resolve by selecting a winner

```bash
curl -s -X POST http://localhost:8000/v1/conflicts/<conflict-id>/resolve \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{"winning_fact_id": "<fact-a-or-fact-b-id>"}' | jq .
```

## Resolve with a fresh value

```bash
curl -s -X POST http://localhost:8000/v1/conflicts/<conflict-id>/resolve \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{"new_value": "dark mode (user confirmed)"}' | jq .
```

## Topics to be covered

- How conflicts are detected at write time
- Resolution strategies: winner selection vs. fresh value (spec §5.10)
- Conflict propagation across federated nodes
- Using the `include_contradicted` query flag

See the [API Reference](/docs/api-reference) for `GET /v1/conflicts` and `POST /v1/conflicts/{id}/resolve`.
