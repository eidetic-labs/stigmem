---
title: §25. Content-Addressed Fact IDs
sidebar_label: §25 Content-Addressed Fact IDs
audience: Spec
description: "Stigmem spec section 25 — SHA-256 CIDs for deduplication, tamper detection, dual UUID/CID addressing."
---

# §25. Content-Addressed Fact IDs {#section-25}

**Status:** DRAFT normative (v1.1-draft, Phase 13)

SHA-256 CIDs for deduplication, tamper detection, dual UUID/CID addressing.

**Authoritative source:** [`spec/stigmem-spec-v1.1-draft.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v1.1-draft.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** DRAFT normative (Phase 13). §25.1–§25.8 carry MUST/SHOULD/MAY normative language.

### §25.1 Scope {#section-25-1}

Content-addressed fact IDs (CIDs) provide a deterministic, tamper-evident identifier for fact records derived from the fact's canonical body. Unlike UUID-style `fact_id` values (which are randomly assigned at write time), a CID can be independently computed from the fact payload and verified without a database lookup.

CIDs enable:
- **Tamper detection**: any modification to a fact's body changes its CID.
- **Deduplication**: identical facts from different federation sources share the same CID.
- **Provenance linkage**: `derived_from` chains (§2.8) can reference CIDs rather than mutable UUIDs.

### §25.2 CID Format {#section-25-2}

#### §25.2.1 Canonical Fact Body {#section-25-2-1}

The **canonical fact body** for CID computation is a JSON object containing
the following fact fields in lexicographic key order per RFC 8785 (JCS — JSON
Canonicalization Scheme). Only the six fields that define *what the fact
asserts* are included; all metadata that varies by node, time, or transport
path is excluded so that two nodes asserting the same knowledge independently
produce the same CID.

```json
{
  "confidence": ...,
  "entity":     ...,
  "relation":   ...,
  "scope":      ...,
  "source":     ...,
  "value":      ...
}
```

The following fields MUST be excluded from the canonical body:

| Field | Reason |
|---|---|
| `fact_id` | Cannot be part of its own CID (circular) |
| `cid` | Cannot be self-referential |
| `hlc` | Node-local logical clock; not part of the fact assertion |
| `timestamp` / `created_at` | Write time; same assertion at different times shares one CID |
| `valid_until` | Expiry policy; does not change what the fact asserts |
| `derived_from` | Provenance pointer; references other fact IDs, creates circularity |
| `attestation_chain` | Transport/provenance concern |
| `source_trust` | Cached derived value, not the fact assertion itself |

The following excluded fields are **security-relevant** and require independent validation — CID coverage alone is not a sufficient tamper check for these fields:

- **`valid_until`**: A malicious peer could extend fact lifetime by modifying this field without changing the CID. Nodes receiving federated facts MUST NOT accept a `valid_until` value that extends beyond any value previously observed for the same CID; changes require a new fact assertion.
- **`derived_from`**: Provenance chain integrity is enforced by verifying each referenced CID independently. A peer could falsify provenance without affecting the CID.
- **`attestation_chain`**: Signatures within the chain are independently verifiable and MUST be re-verified on federation ingest. CID coverage is not a substitute for attestation re-verification.
- **`source_trust`**: MUST be re-computed locally from the source manifest rather than trusted from the federation envelope. Accepting a peer-supplied `source_trust` allows trust score inflation.

#### §25.2.2 Hash Function {#section-25-2-2}

The CID is a prefix-tagged hex-encoded hash of the canonical fact body. The
`sha256:` prefix is included in every CID string so that nodes can detect and
handle future hash-algorithm rotations (§25.2.4) without ambiguity. The CID
MUST be computed as:

```
CID = "sha256:" + hex_lowercase(SHA-256(RFC8785(canonical_fact_body)))
```

Where:
- `RFC8785(...)` produces the deterministic UTF-8 JSON byte string per RFC 8785.
- `SHA-256` is the SHA-2 family 256-bit hash function (FIPS 180-4).
- `hex_lowercase` encodes the 32-byte digest as 64 lowercase hexadecimal characters.
- The `"sha256:"` prefix MUST be included to allow future hash-algorithm rotation (see §25.2.4 and §22.2).

Example:
```
fact = { "entity": "user:alice", "relation": "memory:prefers",
         "value": "dark mode", "scope": "company",
         "source": "agent:assistant-01", "confidence": 0.95 }

CID = "sha256:4e9a2c1f8b3d0e7a5c6f1d2b9e8a3c4f7b0d1e6a9c2f5b8e1d4a7c0f3b6e9a2c"
```

*(The hex value above is illustrative; implementations MUST compute the actual SHA-256.)*

#### §25.2.3 `value` Field Canonicalization {#section-25-2-3}

When the fact `value` field is of type `text` or `string`, it MUST be included as a JSON string with no additional normalization (Unicode form is preserved). When `value` is of type `ref`, it MUST be included as its resolved URI string. When `value` is `null`, it MUST be included as JSON `null`. All numeric `confidence` values MUST use standard JSON number encoding (no trailing zeros beyond single precision).

#### §25.2.4 Future Hash-Algorithm Rotation {#section-25-2-4}

If SHA-256 is deprecated, nodes MUST:

1. Follow the dual-trust rollover pattern (§22.2): accept both the old and new hash function during a transition window of at least 90 days.
2. Introduce a new prefix (e.g. `"sha3-256:"`) for the new hash function.
3. Publish a migration notice in the spec changelog with the new prefix, the transition window start date, and the SHA-256 sunset date.

### §25.3 Migration Path {#section-25-3}

#### §25.3.1 Alias Table {#section-25-3-1}

During the migration window both UUID-style `fact_id` and content-addressed
CID must be valid addressing keys. The `fact_cid_aliases` table provides this
dual-addressing: a unique index on `cid` allows O(1) lookup by CID, while the
existing primary key on `facts.id` continues to serve UUID-based lookups. A new
nullable `cid` column is also added directly to the `facts` table for
single-join access patterns.

```sql
-- Migration 013b: Content-addressed fact IDs
ALTER TABLE facts ADD COLUMN cid TEXT;      -- nullable during backfill window

CREATE TABLE fact_cid_aliases (
  fact_id  TEXT NOT NULL REFERENCES facts(fact_id),
  cid      TEXT NOT NULL,
  PRIMARY KEY (fact_id, cid)
);

CREATE UNIQUE INDEX idx_fact_cid_aliases_cid ON fact_cid_aliases(cid);
```

Every new fact written MUST have a corresponding row in `fact_cid_aliases`. Existing facts (pre-Phase 13) will have `cid IS NULL` until the backfill runner completes (§25.7.2).

#### §25.3.2 Dual-Addressing During Migration Window {#section-25-3-2}

During the migration window (until a deployment-configurable end-date; SHOULD be at least **12 months** from Phase 13 GA):

1. Nodes MUST accept both a `fact_id` (UUID-style, e.g. `"fact_01J..."`) and a `cid` (`"sha256:..."`) as addressing keys in all API routes that accept a fact identifier.
2. A lookup by CID MUST go through the `fact_cid_aliases` index.
3. A lookup by `fact_id` MUST behave identically to pre-Phase-13 behavior.
4. Nodes MAY include both `fact_id` and `cid` in all fact record responses during the migration window.

After the migration window, `fact_id`-only addressing SHOULD be deprecated; a future spec revision will formalize the removal timeline.

#### §25.3.3 `cid` Field on FactRecord {#section-25-3-3}

A `cid` field MUST be added to the `FactRecord` schema (v1.1 Phase 13
addition). The field is nullable only to accommodate pre-Phase-13 records that
have not yet been backfilled (§25.7.2); all new facts MUST be written with a
non-null CID.

```
FactRecord (Phase 13 addition):
  ...all prior fields...
  cid: string | null   // "sha256:<hex64>"; null only for pre-Phase-13 records pending backfill
```

New facts MUST be written with a non-null `cid`. Pre-Phase-13 facts will have `cid: null` until the backfill migration completes.

### §25.4 Federation Envelope Extensions {#section-25-4}

#### §25.4.1 CID in Federation Payloads {#section-25-4-1}

The federation fact envelope (§5, §6) MUST carry the `cid` field alongside
the legacy `fact_id` for the duration of the migration window. Receiving nodes
MUST independently recompute the CID from the inbound fact body and reject
facts where the declared CID does not match — this provides tamper detection
at the federation boundary without requiring a round-trip to the originating
node.

```json
{
  "fact_id":  "fact_01J...",
  "cid":      "sha256:4e9a2c...",
  "entity":   "user:alice",
  "relation": "memory:prefers",
  ...other fact fields...
}
```

Receiving nodes MUST independently compute the CID from the inbound fact body (§25.2.2) and compare it against the `cid` field:

1. If the CIDs match, the fact is accepted as unmodified.
2. If the CIDs do not match, the fact MUST be rejected; the node MUST emit a `cid_mismatch` audit log event (§22.3) and SHOULD alert the operator.
3. The federation envelope MUST include a `phase13_ga_at` field (ISO 8601) indicating the origin node's Phase 13 GA timestamp. Receiving nodes MUST reject facts with `cid: null` where `fact.created_at >= phase13_ga_at`, emitting a `cid_mismatch` audit event (§22.3). Facts with `cid: null` where `fact.created_at < phase13_ga_at` are accepted as legitimate pre-Phase-13 legacy records. Nodes MUST NOT silently accept a fact with `cid: null` whose `created_at` postdates the declared `phase13_ga_at`. This prevents malicious peers from bypassing tamper detection by stripping the `cid` field and claiming a post-Phase-13 fact is a legacy record.

#### §25.4.2 `derived_from` CID References {#section-25-4-2}

The `derived_from` field (§2.8) MAY carry CIDs in addition to, or instead of, UUID-style `FactHash` values during the migration window. Nodes MUST accept both formats in `derived_from` arrays. After the migration window, CIDs are the preferred `derived_from` format.

### §25.5 Storage-Trait Extensions {#section-25-5}

The following storage-trait methods MUST be extended or added. `get_fact` is
broadened to accept either addressing format. `assert_fact` now computes and
persists the CID atomically. `compute_cid` is exposed as a standalone utility
so that federation receivers and the backfill runner can recompute CIDs without
going through the full write path.

```
get_fact(id: string) → FactRecord | null
  // MUST accept both "fact_01J..." (UUID-style) and "sha256:..." (CID)

assert_fact(fact: FactInput) → FactRecord
  // MUST compute and persist cid on every write (Phase 13 forward)

compute_cid(body: CanonicalFactBody) → string
  // utility: returns "sha256:<hex64>" for the given canonical body
```

### §25.6 Wire Format {#section-25-6}

#### §25.6.1 Lookup by CID or fact_id {#section-25-6-1}

The existing single-fact endpoint (§5.5) is extended to accept either a
UUID-style `fact_id` or a `sha256:` CID in the path parameter. The node
detects the format by prefix: strings starting with `sha256:` are routed
through the CID alias index; all others use the primary key.

```
GET /v1/facts/:cid_or_fact_id
Authorization: Bearer <agent or admin api-key>

→ 200 { ...FactRecord with both fact_id and cid populated... }
→ 400 cid_malformed   if a "sha256:..." string is not a valid hex64 CID
→ 404 fact_not_found
```

#### §25.6.2 Verify CID {#section-25-6-2}

An on-demand integrity check that recomputes the CID from the stored fact body
and compares it against the persisted CID. This endpoint is useful for
periodic data-integrity audits and for investigating `cid_mismatch` alerts
from the federation layer. A `cid_valid: false` response indicates either
data corruption or a canonicalization bug and SHOULD trigger an operator
investigation.

```
POST /v1/facts/:fact_id/verify-cid
Authorization: Bearer <agent or admin api-key>

→ 200 { "cid_valid": true,
         "computed_cid": "sha256:...", "stored_cid": "sha256:..." }
→ 200 { "cid_valid": false,
         "computed_cid": "sha256:...", "stored_cid": "sha256:...",
         "mismatch_reason": "stored_cid does not match computed_cid" }
→ 404 fact_not_found
```

Any `cid_valid: false` response SHOULD trigger an operator audit investigation.

#### §25.6.3 Backfill Status {#section-25-6-3}

Reports the progress of the CID backfill runner (§25.7.2). Operators use this
endpoint to monitor migration progress and to determine when the node has
achieved full CID coverage for its fact store.

```
GET /v1/admin/cid-backfill/status
Authorization: Bearer <admin api-key>

→ 200 {
    "total_facts":       12340,
    "backfilled_facts":  12340,
    "remaining_facts":   0,
    "backfill_complete": true,
    "last_updated_at":   "2026-05-04T12:00:00Z"
  }
```

### §25.7 Migration Procedure {#section-25-7}

#### §25.7.1 Schema Migration {#section-25-7-1}

Run Migration 013b (§25.3.1 DDL) as part of the Phase 13 upgrade. The full upgrade batch MUST apply migrations in order: 013a (tombstones, §23.5.3), then 013b (CID aliases, §25.3.1), then 013c (retraction log, §23.5.3). 013a and 013c MUST both be applied before 013b to maintain foreign-key integrity.

#### §25.7.2 Backfill Runner {#section-25-7-2}

Implementations MUST provide a `stigmem backfill-cids` CLI command that:

1. Iterates over all facts in the `facts` table where `cid IS NULL`.
2. For each fact, computes the CID from the canonical fact body (§25.2.1).
3. Writes the `cid` to `facts.cid` and inserts a row into `fact_cid_aliases`, both in a single transaction per batch.
4. Operates in batches of 1000 facts with a configurable rate limit to avoid I/O saturation.
5. Is idempotent: re-running on a partially backfilled table continues from the last unprocessed row.
6. Reports progress via `GET /v1/admin/cid-backfill/status` (§25.6.3).

The backfill MAY run concurrently with live fact writes. The write-path CID assignment for new facts (§25.7.3) MUST proceed regardless of backfill state.

#### §25.7.3 Online Write Path {#section-25-7-3}

From Phase 13 forward, `assert_fact` MUST:

1. Compute the CID before writing to the `facts` table.
2. Write the `cid` column in the same transaction as all other fact fields.
3. Insert a row into `fact_cid_aliases` in the same transaction.
4. On CID collision (same CID, different `fact_id`): check whether the existing fact body is identical. If identical, return the existing record (idempotent upsert). If the bodies differ, this is a hash collision: the node MUST emit a `cid_collision_detected` audit event and MUST NOT overwrite the existing fact.

### §25.8 Error Reference {#section-25-8}

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `cid_malformed` | CID string is not a valid `"sha256:<hex64>"` format |
| 400 | `cid_mismatch` | Inbound federated fact's `cid` does not match the independently computed CID |
| 404 | `fact_not_found` | Fact ID (UUID or CID) not found |
| 409 | `cid_collision_detected` | Two different fact bodies produced the same CID (hash collision); reject write and emit audit event |

---

## Appendix A. Security Policy

*Content unchanged from v1.0 §19 (non-normative).*

The active security policy — supported versions, vulnerability reporting instructions, scope definitions, and the coordinated disclosure timeline — is maintained in [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md) at the root of the repository.

**Reporting:** Do not open a public GitHub issue for security vulnerabilities. Report via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories). We acknowledge within 48 hours and target a patch within 14 days for critical vulnerabilities.

**Disclosure timeline:** 90 days from the report date before public disclosure, except for vulnerabilities already being actively exploited in the wild.

For the current security posture and Dependabot alert triage covering v1.0-rc, see the [Security Posture section of SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md#security-posture--v10-rc-2026-05-03).

---
