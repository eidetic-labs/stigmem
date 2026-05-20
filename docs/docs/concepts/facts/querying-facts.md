---
title: Querying Facts
sidebar_label: Querying Facts
audience: Integrator
---

# Querying Facts

<p className="stigmem-meta"><span>1 min read</span><span>Agent developer</span><span>Spec-03-HTTP-API</span></p>

<div className="stigmem-lead">

**What this page is**

Quick reference for the `GET /v1/facts` query API.

</div>

:::info Coming soon
Full guide content is planned for the next docs sprint.
:::

## Quick example

```bash
# All facts for a specific entity
curl -s 'http://localhost:8000/v1/facts?entity=user:alice' \
  -H 'Authorization: Bearer dev-key' | jq .facts

# Filter by entity + relation
curl -s 'http://localhost:8000/v1/facts?entity=user:alice&relation=memory:prefers' \
  -H 'Authorization: Bearer dev-key' | jq '.facts[0].value'

# Only high-confidence facts
curl -s 'http://localhost:8000/v1/facts?min_confidence=0.8' \
  -H 'Authorization: Bearer dev-key' | jq .
```

## Topics to be covered

<div className="stigmem-grid">

<div><h4>Filtering</h4><p>By entity, relation, source, scope (see Spec-03-HTTP-API query-facts route).</p></div>
<div><h4>Pagination</h4><p>Cursor-based via the <code>cursor</code> field.</p></div>
<div><h4>Polling for new facts</h4><p>With the <code>after</code> HLC cursor.</p></div>
<div><h4>Including contradicted and expired facts</h4></div>
<div><h4>Scoped access</h4><p>Local vs. company facts.</p></div>

</div>

See the [API Reference](/docs/reference/api) for the full
`GET /v1/facts` endpoint spec.
