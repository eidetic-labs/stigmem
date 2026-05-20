---
title: Conflict Resolution
sidebar_label: Conflict Resolution
audience: Integrator
---

# Conflict Resolution

<p className="stigmem-meta"><span>2 min read</span><span>Agent developer · Node operator</span><span>Spec-15 + Spec-03</span></p>

<div className="stigmem-lead">

**What this page is**

A quick reference for managing contradictory facts via the conflict
API. See [Conflict Semantics](./conflict-semantics) for the underlying
detection and resolution model.

</div>

:::info Coming soon
Full guide content is planned for the next docs sprint.
:::

## What is a conflict?

A conflict occurs when two facts share the same
`(entity, relation, scope)` tuple but carry different values.
Stigmem stores both facts and creates a `ConflictRecord` — it never
silently overwrites. See Spec-15-Fact-Semantics and the conflict
routes in Spec-03-HTTP-API.

<div className="stigmem-keypoint">

**Reserved-namespace exemption.**

Facts whose entity or relation begins with the bare
<code>stigmem:</code> prefix (e.g., <code>stigmem:conflict:status</code>,
<code>stigmem:resolves</code>) are exempt from sibling-detection.
These are protocol state transitions, not semantic content.
<code>stigmem://</code> URI entities (user-created content) are
<strong>not</strong> exempt and are subject to normal contradiction
detection.

</div>

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

<div className="stigmem-grid">

<div><h4>Conflict detection at write time</h4></div>
<div><h4>Resolution strategies</h4><p>Winner selection vs. fresh value (Spec-03-HTTP-API conflict resolution route).</p></div>
<div><h4>Conflict propagation across federated nodes</h4></div>
<div><h4>Using the <code>include_contradicted</code> query flag</h4></div>

</div>

See the [API Reference](/docs/reference/api) for `GET /v1/conflicts`
and `POST /v1/conflicts/{id}/resolve`.
