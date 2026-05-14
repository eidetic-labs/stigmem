---
title: Conflict Resolution
sidebar_label: Conflict Resolution
audience: Integrator
---

# Conflict Resolution

**Audience:** Agent developers and node operators managing contradictory facts.

:::info Coming soon
Full guide content is planned for the next docs sprint.
:::

## What is a conflict?

A conflict occurs when two facts share the same (entity, relation, scope) tuple but carry different values. Stigmem stores both facts and creates a `ConflictRecord` — it never silently overwrites. See Spec-15-Fact-Semantics and the conflict routes in Spec-03-HTTP-API.

**Reserved-namespace exemption:** Facts whose entity or relation begins with the bare `stigmem:` prefix (e.g., `stigmem:conflict:status`, `stigmem:resolves`) are exempt from sibling-detection. These are protocol state transitions, not semantic content. Note that `stigmem://` URI entities (user-created content) are **not** exempt and are subject to normal contradiction detection. See Spec-03-HTTP-API conflict resolution route.

## List open conflicts

```bash
curl -s 'http://localhost:8000/v1/conflicts?status=open' \
  -H 'Authorization: Bearer dev-key' | jq .
```

## Resolve by selecting a winner

```bash
curl -s -X POST http://localhost:8000/v1/conflicts/<conflict-id>/resolve \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-key' \
  -d '{"winning_fact_id": "<fact-a-or-fact-b-id>"}' | jq .
```

## Resolve with a fresh value

```bash
curl -s -X POST http://localhost:8000/v1/conflicts/<conflict-id>/resolve \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-key' \
  -d '{"new_value": "dark mode (user confirmed)"}' | jq .
```

## Topics to be covered

- How conflicts are detected at write time
- Resolution strategies: winner selection vs. fresh value (Spec-03-HTTP-API conflict resolution route)
- Conflict propagation across federated nodes
- Using the `include_contradicted` query flag

See the [API Reference](/docs/reference/api) for `GET /v1/conflicts` and `POST /v1/conflicts/{id}/resolve`.
