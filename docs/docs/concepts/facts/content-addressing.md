---
title: Content-Addressed Fact IDs
sidebar_label: Content Addressing
sidebar_position: 10
description: How Stigmem uses SHA-256 content-addressed IDs for tamper detection, deduplication, and provenance linkage.
---

# Content-Addressed Fact IDs

**Audience:** Protocol implementers and security-focused operators.

## The problem

Stigmem assigns a random UUID to each fact at write time. That UUID is opaque — it tells you nothing about the fact's content. If a fact is modified in transit (e.g., during federation), the UUID doesn't change. If two nodes independently assert identical facts, they get different UUIDs. And if a provenance chain references a fact by UUID, you can't verify the reference without a database lookup.

You need an identifier that is derived from the content itself: deterministic, verifiable, and tamper-evident.

## Naive approaches and why they fail

**Hash the entire fact record.** Include every field — timestamps, HLC, garden assignments, trust scores. Now the hash changes when metadata changes, even if the core assertion is identical. Two identical assertions at different times get different hashes. Federation deduplication fails.

**Hash only the value field.** Too narrow. Two different entities could assert the same value for different relations. The hash wouldn't distinguish them.

**Use the UUID as a fingerprint.** UUIDs are assigned, not derived. You can't recompute a UUID from the fact content. This makes independent verification impossible — you must trust the issuing node.

## Our model

Stigmem computes a **content-addressed ID (CID)** from a canonical subset of fact fields using SHA-256:

```
CID = "sha256:" + hex(SHA-256(RFC8785(canonical_body)))
```

The canonical body includes exactly six fields:

```json
{
  "confidence": 0.95,
  "entity":     "stigmem://company.example/user/alice",
  "relation":   "memory:prefers",
  "scope":      "company",
  "source":     "stigmem://company.example/agent/assistant",
  "value":      {"type": "string", "v": "dark mode"}
}
```

These six fields define *what was asserted, by whom, at what confidence, in what scope*. Everything else — timestamps, HLC, garden membership, trust scores, provenance links — is metadata about the assertion, not the assertion itself.

### Canonical encoding

The canonical body is serialized using **RFC 8785 (JSON Canonicalization Scheme)**: deterministic key ordering, no whitespace, UTF-8. This ensures that any implementation computing the CID from the same six fields produces the same bytes, and therefore the same hash.

The `"sha256:"` prefix enables future hash-algorithm rotation (e.g., `"sha3-256:"`) following the dual-trust rollover pattern from Spec-10-Hardening.

### Worked example: computing a CID

```python
import hashlib
import json

fact_body = {
    "confidence": 0.95,
    "entity": "stigmem://company.example/user/alice",
    "relation": "memory:prefers",
    "scope": "company",
    "source": "stigmem://company.example/agent/assistant",
    "value": {"type": "string", "v": "dark mode"}
}

canonical = json.dumps(fact_body, sort_keys=True, separators=(",", ":"))
digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
cid = f"sha256:{digest}"
# cid = "sha256:4e9a2c1f..." (64 hex chars)
```

### Federation tamper detection

When a fact is replicated between nodes, the federation envelope carries both the legacy `fact_id` (UUID) and the `cid`:

```mermaid
sequenceDiagram
    participant A as Node A (sender)
    participant B as Node B (receiver)
    A->>B: Federation envelope<br/>{fact_id, cid, entity, relation, value, ...}
    B->>B: Recompute CID from<br/>received fact body
    alt CIDs match
        B->>B: Accept fact
    else CIDs don't match
        B->>B: Reject + emit<br/>cid_mismatch audit event
    end
```

The receiving node independently computes the CID from the inbound fact body. If it doesn't match the declared `cid`, the fact has been tampered with in transit and is rejected.

### Deduplication

Identical assertions from different federation sources share the same CID. If Node A and Node B both assert the same fact (same six fields), they produce the same CID. The receiving node can detect this and avoid creating duplicates, even though the `fact_id` UUIDs are different.

### Dual addressing during migration

The CID is introduced alongside the existing UUID system. During a 12-month migration window, both `fact_id` and `cid` are accepted as addressing keys:

```bash
# Lookup by UUID (legacy)
curl $STIGMEM_URL/v1/facts/fact_01J...

# Lookup by CID (new)
curl $STIGMEM_URL/v1/facts/sha256:4e9a2c1f...

# Verify CID integrity
curl -X POST $STIGMEM_URL/v1/facts/fact_01J.../verify-cid
# → {"cid_valid": true, "computed_cid": "sha256:...", "stored_cid": "sha256:..."}
```

Existing pre-CID facts have `cid: null` until the backfill migration runs. New facts are always written with a CID.

## Why this is non-obvious

**Excluding timestamps from the CID is deliberate.** The same assertion made at two different times should have the same CID — it's the same knowledge claim. Including timestamps would make every assertion unique, defeating deduplication and making provenance linkage brittle.

**Excluding `derived_from` prevents circularity.** If CID computation included `derived_from` (which references other fact CIDs), you'd need to know all ancestor CIDs before computing the current CID — and adding a new derivation link would change the CID. Excluding it keeps CID computation O(1) and non-recursive.

**Some excluded fields are security-relevant.** `valid_until`, `derived_from`, `attestation_chain`, and `source_trust` are excluded from the CID but still need independent validation. A malicious peer could modify `valid_until` to extend a fact's lifetime without changing its CID. Spec-21-Content-Addressed-IDs.2.1 documents per-field validation requirements for each excluded field.

**The `"sha256:"` prefix looks redundant today.** It exists for algorithm agility. If SHA-256 is ever deprecated, nodes can introduce `"sha3-256:"` and run a dual-trust transition period where both are accepted. Without the prefix, you'd need a flag day where all nodes switch simultaneously.

## What it costs

- **Compute overhead.** One SHA-256 hash per fact write. Negligible on modern hardware (~200ns per hash).
- **Storage.** A 71-character CID string (`"sha256:" + 64 hex chars`) per fact, plus a row in the `fact_cid_aliases` table. Modest overhead.
- **Migration effort.** Existing facts need a backfill (`stigmem backfill-cids` CLI). For large fact stores, this runs in batches of 1,000 with configurable rate limiting. The backfill is idempotent and can run concurrently with live writes.
- **Hash collision risk.** SHA-256 has a 2^128 collision resistance. A collision means two different facts produce the same CID. The node handles this by comparing the full fact body on collision and rejecting the second fact if bodies differ. In practice, this will never occur at knowledge-fabric scale.

## References

- Spec-21-Content-Addressed-IDs.1 — CID scope and benefits (tamper detection, deduplication, provenance linkage)
- Spec-21-Content-Addressed-IDs.2 — CID format (canonical body, hash function, field canonicalization, algorithm rotation)
- Spec-21-Content-Addressed-IDs.3 — Migration path (alias table, dual addressing, `cid` field on FactRecord)
- Spec-21-Content-Addressed-IDs.4 — Federation envelope extensions (CID in payloads, `derived_from` CID references)
- Spec-21-Content-Addressed-IDs.7 — Migration procedure (schema migration, backfill runner, online write path)
- Spec-05-Federation-Trust.6.2 — Fact hash computation (the pre-CID hash format used in provenance chains)
