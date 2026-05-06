---
title: Content-Addressed Fact IDs (CIDs)
sidebar_label: Content Addressing
description: Deterministic content-addressed identifiers for facts — deduplication, integrity verification, and external citation (spec §25).
audience: Integrator
---

# Content-Addressed Fact IDs (CIDs)

**Audience:** Integrators building deduplication pipelines, federation operators verifying fact integrity, and anyone citing facts by content hash.

Every fact in Stigmem receives a **content identifier (CID)** — a deterministic SHA-256 hash of its canonical body. Two facts with the same entity, relation, value, source, and scope always produce the same CID, regardless of when or where they were asserted. The full protocol is defined in spec §25.

---

## CID format

```
sha256:<64 hex chars>
```

Example:

```
sha256:a3f2b8c901d4e5f6789012345678abcdef0123456789abcdef0123456789abcd
```

---

## Canonical body (§25.2.2)

The CID is computed over a JSON object with exactly **6 fields** in lexicographic key order, serialized with RFC 8785 (JCS) determinism:

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

**Excluded fields** (§25.2.1):

| Field | Why excluded |
|-------|-------------|
| `fact_id`, `cid` | Circular — the CID cannot include itself |
| `created_at` / `timestamp` | Same assertion at different times shares one CID |
| `confidence` | Confidence can change; CID should not |
| `valid_until` | Expiry is operational, not content-defining |
| `derived_from` | Provenance chain requires independent validation |
| `attestation_chain` | Security-relevant; validated separately |
| `source_trust` | Trust score is context-dependent |
| `signature` | Validated independently of content identity |
| `reason` | Retraction/tombstone reason is metadata |

---

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

---

## Dual addressing — UUID and CID

Every fact has both a UUID (`id`) and a CID. You can fetch a fact by either:

```bash
# By UUID
curl -s http://localhost:8765/v1/facts/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"

# By CID
curl -s http://localhost:8765/v1/facts/sha256:a3f2b8c9... \
  -H "Authorization: Bearer $TOKEN"
```

The node resolves CIDs via the `fact_cid_aliases` table, which maps each CID to its UUID.

---

## Write-path deduplication (§25.7.3)

When you assert a fact, the node:

1. Computes the CID from the 6 canonical fields.
2. Checks `fact_cid_aliases` for an existing fact with the same CID.
3. If found, returns the **existing** fact (idempotent write).
4. If not found, inserts the new fact, stores its CID, and creates the alias.

This means asserting the same (entity, relation, value, source, scope) tuple twice returns the same fact record — no duplicates.

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

---

## CID verification

The node can verify that a stored fact's CID matches a freshly computed CID:

```bash
curl -s http://localhost:8765/v1/facts/sha256:a3f2b8c9.../verify \
  -H "Authorization: Bearer $TOKEN"
```

If the CID diverges from the stored canonical body, the node emits a `cid_mismatch` audit event.

---

## Federation and tamper detection (§25.4)

Federation envelopes carry the CID for each fact. The receiving node:

1. Computes the CID independently from the envelope's canonical fields.
2. Compares it against the envelope's declared CID.
3. Rejects the fact if they diverge — this detects tampering in transit.

Facts with `cid: null` whose `created_at` is after the Phase 13 GA date are rejected. Legacy facts (pre-Phase 13) with `cid: null` are accepted during the backfill window.

---

## CID backfill (§25.7.2)

Existing facts created before Phase 13 do not have CIDs. The node backfills them in the background:

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

The backfill runs concurrently with live writes. The migration window is 12 months (§25.7.2). After the window closes, all facts must have CIDs.

---

## External citation

CIDs are stable, content-derived identifiers that work across nodes. Use them to cite facts in external systems:

```
stigmem://node.example.com/facts/sha256:a3f2b8c901d4e5f6...
```

Because the CID is derived from content, the same fact on two federated nodes has the same CID — making cross-node references unambiguous.

---

## See also

- [Time-Travel Queries](./time-travel.md) — query historical fact state
- [RTBF Tombstones](./rtbf.md) — entity erasure
- [Source Attestation](./source-attestation.md) — provenance and trust
- [API Reference](/docs/reference/api) — full endpoint documentation
