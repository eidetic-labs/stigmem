---
title: Content-Addressed Fact IDs (CIDs)
sidebar_label: Content Addressing
description: Deterministic content-addressed identifiers for facts — deduplication, integrity verification, and external citation (Spec-21-Content-Addressed-IDs).
audience: Integrator
---

# Content-Addressed Fact IDs (CIDs)

<p className="stigmem-meta"><span>5 min read</span><span>Integrator · Federation operator</span><span>Spec-21-Content-Addressed-IDs</span></p>

<div className="stigmem-lead">

**What this page is**

Practical guide to computing and using CIDs. Every fact in Stigmem
receives a deterministic SHA-256 hash of its canonical body. Two
facts with the same entity, relation, value, source, and scope always
produce the same CID, regardless of when or where they were
asserted. For the design rationale, see
[Content Addressing concepts](./content-addressing).

</div>

## CID format

```
sha256:<64 hex chars>
```

Example:

```
sha256:a3f2b8c901d4e5f6789012345678abcdef0123456789abcdef0123456789abcd
```

## Canonical body

The CID is computed over a JSON object with exactly **6 fields** in
lexicographic key order, serialized with RFC 8785 (JCS) determinism:

```json
{
  "entity": "user:alice",
  "relation": "memory:role",
  "scope": "local",
  "source": "agent:assistant",
  "value_type": "string",
  "value_v": "engineer"
}
```

### Excluded fields

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Why excluded</dd>
</div>

<div>
<dt><code>fact_id</code>, <code>cid</code></dt>
<dt><span className="stigmem-fields__type">circular</span></dt>
<dd>The CID cannot include itself.</dd>
</div>

<div>
<dt><code>created_at</code> / <code>timestamp</code></dt>
<dt><span className="stigmem-fields__type">temporal metadata</span></dt>
<dd>Same assertion at different times shares one CID.</dd>
</div>

<div>
<dt><code>confidence</code></dt>
<dt><span className="stigmem-fields__type">mutable signal</span></dt>
<dd>Confidence can change; CID should not.</dd>
</div>

<div>
<dt><code>valid_until</code></dt>
<dt><span className="stigmem-fields__type">operational</span></dt>
<dd>Expiry is operational, not content-defining.</dd>
</div>

<div>
<dt><code>derived_from</code></dt>
<dt><span className="stigmem-fields__type">provenance chain</span></dt>
<dd>Requires independent validation.</dd>
</div>

<div>
<dt><code>attestation_chain</code></dt>
<dt><span className="stigmem-fields__type">security</span></dt>
<dd>Security-relevant; validated separately.</dd>
</div>

<div>
<dt><code>source_trust</code></dt>
<dt><span className="stigmem-fields__type">contextual</span></dt>
<dd>Trust score is context-dependent.</dd>
</div>

<div>
<dt><code>signature</code></dt>
<dt><span className="stigmem-fields__type">authenticity</span></dt>
<dd>Validated independently of content identity.</dd>
</div>

<div>
<dt><code>reason</code></dt>
<dt><span className="stigmem-fields__type">metadata</span></dt>
<dd>Retraction/tombstone reason.</dd>
</div>

</div>

## Computing a CID

### Python

```python
import hashlib
import json

def compute_cid(entity, relation, value_type, value_v, source, scope):
    body = {
        "entity": entity,
        "relation": relation,
        "scope": scope,
        "source": source,
        "value_type": value_type,
        "value_v": value_v,
    }
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return f"sha256:{digest}"

cid = compute_cid(
    entity="user:alice",
    relation="memory:role",
    value_type="string",
    value_v="engineer",
    source="agent:assistant",
    scope="local",
)
print(cid)  # sha256:...
```

### TypeScript

```ts
import { createHash } from "crypto";

function computeCid(
  entity: string, relation: string,
  valueType: string, valueV: string,
  source: string, scope: string,
): string {
  const body = { entity, relation, scope, source, value_type: valueType, value_v: valueV };
  const canonical = JSON.stringify(body, Object.keys(body).sort());
  const digest = createHash("sha256").update(canonical).digest("hex");
  return `sha256:${digest}`;
}
```

### Go

```go
import (
    "crypto/sha256"
    "encoding/json"
    "fmt"
)

func computeCID(entity, relation, valueType, valueV, source, scope string) string {
    body := map[string]string{
        "entity": entity, "relation": relation, "scope": scope,
        "source": source, "value_type": valueType, "value_v": valueV,
    }
    canonical, _ := json.Marshal(body) // keys sorted by Go's map iteration after json.Marshal
    digest := sha256.Sum256(canonical)
    return fmt.Sprintf("sha256:%x", digest)
}
```

## Dual addressing — UUID and CID

Every fact has both a UUID (`id`) and a CID. You can fetch a fact by
either.

```bash
# By UUID
curl -s http://localhost:8765/v1/facts/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"

# By CID
curl -s http://localhost:8765/v1/facts/sha256:a3f2b8c9... \
  -H "Authorization: Bearer $TOKEN"
```

The node resolves CIDs via the `fact_cid_aliases` table, which maps
each CID to its UUID.

## Write-path deduplication

When you assert a fact, the node:

<ol className="stigmem-steps">
<li>Computes the CID from the 6 canonical fields.</li>
<li>Checks <code>fact_cid_aliases</code> for an existing fact with the same CID.</li>
<li>If found, returns the <strong>existing</strong> fact (idempotent write).</li>
<li>If not found, inserts the new fact, stores its CID, and creates the alias.</li>
</ol>

<div className="stigmem-keypoint">

**Asserting the same (entity, relation, value, source, scope) tuple twice returns the same fact record — no duplicates.**

</div>

```bash
# First assertion — creates the fact
curl -s -X POST http://localhost:8765/v1/facts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity":"user:alice","relation":"memory:role","value":{"type":"string","v":"engineer"},"source":"agent:assistant","scope":"local"}' \
  | jq '{id, cid}'

# Second identical assertion — returns the same fact
curl -s -X POST http://localhost:8765/v1/facts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity":"user:alice","relation":"memory:role","value":{"type":"string","v":"engineer"},"source":"agent:assistant","scope":"local"}' \
  | jq '{id, cid}'
# Same id and cid as above
```

## CID verification

The node can verify that a stored fact's CID matches a freshly
computed CID:

```bash
curl -s http://localhost:8765/v1/facts/sha256:a3f2b8c9.../verify \
  -H "Authorization: Bearer $TOKEN"
```

If the CID diverges from the stored canonical body, the node emits a
`cid_mismatch` audit event.

## Federation and tamper detection

Federation envelopes carry the CID for each fact. The receiving node:

<ol className="stigmem-steps">
<li>Computes the CID independently from the envelope's canonical fields.</li>
<li>Compares it against the envelope's declared CID.</li>
<li>Rejects the fact if they diverge — this detects tampering in transit.</li>
</ol>

Facts with `cid: null` whose `created_at` falls after CID enforcement
begins are rejected. Legacy pre-CID facts with `cid: null` are
accepted during the backfill window.

## CID backfill

Existing facts created before the pre-reset design window do not have
CIDs. The node backfills them in the background.

```bash
# Check backfill progress
curl -s http://localhost:8765/v1/admin/cid-backfill/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
```

Response:

```json
{
  "total_facts": 12500,
  "backfilled_facts": 11200,
  "pending_facts": 1300,
  "backfill_complete": false
}
```

The backfill runs concurrently with live writes. The migration window
is 12 months. After the window closes, all facts must have CIDs.

## External citation

CIDs are stable, content-derived identifiers that work across nodes.
Use them to cite facts in external systems.

```
stigmem://node.example.com/facts/sha256:a3f2b8c901d4e5f6...
```

<div className="stigmem-keypoint">

**Because the CID is derived from content, the same fact on two federated nodes has the same CID** — making cross-node references unambiguous.

</div>

## See also

<div className="stigmem-next">

<a href="./content-addressing">
<strong>Concepts</strong>
<span>Why content addressing</span>
<small>Design rationale: failure modes of UUIDs and how SHA-256 fixes them.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/time-travel">
<strong>Experimental</strong>
<span>Time-travel queries</span>
<small>Query historical fact state.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/source-attestation">
<strong>Experimental</strong>
<span>Source attestation</span>
<small>Provenance and trust.</small>
</a>

<a href="/docs/reference/api">
<strong>Reference</strong>
<span>HTTP API</span>
<small>Full endpoint documentation.</small>
</a>

</div>
