---
spec_id: Spec-X2-RTBF-Tombstones
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0bN
last_updated: 2026-05-14
supersedes: pre-reset §23 right-to-be-forgotten tombstone material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-05-Federation-Trust >= 0.1.0-alpha.0
  - Spec-09-Audit-Log >= 0.1.0-alpha.0
title: §23. Right-to-be-Forgotten Tombstones
sidebar_label: §23 Right-to-be-Forgotten Tombstones
audience: Spec
description: "Stigmem spec section 23 — Cryptographic tombstones, recall-time suppression, federation propagation, legal-hold mode."
stability: experimental
since: 0.9.0a1
---

# §23. Right-to-be-Forgotten Tombstones {#section-23}

**Status:** Experimental / opt-in source package on `main`

Cryptographic tombstones, recall-time suppression, federation propagation, legal-hold mode.

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for RTBF tombstone semantics.

:::caution EXPERIMENTAL
The tombstone signing format and federation propagation rules are still under security review. Until §23 reaches GA:

- Do **not** rely on tombstone federation for compliance workflows in multi-node deployments.
- Tombstone `DELETE` operations are locally reliable; cross-node propagation is best-effort.
- Operators with GDPR/CCPA obligations should implement manual deletion coordination across nodes until federation is confirmed correct.
:::

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** Experimental. §23.1–§23.7 preserve proposed MUST/SHOULD/MAY language for ADR-008 review, but they are not part of the supported default install.

### §23.1 Scope {#section-23-1}

This section defines the tombstone mechanism for compliance with right-to-be-forgotten (RTBF) obligations under data-protection frameworks (e.g., GDPR Art. 17, CCPA §1798.105). A **tombstone** is a signed, durable record that directs every node in the federation to suppress facts about a specified entity from all future recall responses.

Tombstones are a protocol primitive, not a legal determination. Operators MUST obtain appropriate legal guidance before issuing or refusing tombstone requests.

### §23.2 Tombstone Record Shape {#section-23-2}

#### §23.2.1 Schema {#section-23-2-1}

A tombstone record is a self-contained, cryptographically signed directive. It
identifies the target entity, the scopes to suppress, and the admin who
authorised the erasure. The `signature` field covers the canonical JSON of all
other fields (except `reason`, which is excluded to allow redaction during
federation rebroadcast — see §23.2.4). The `key_id` is included in the signed
body so that verifiers can resolve the correct historical signing key without
trial-verifying against the entire rotation chain.

```
TombstoneRecord:
  id:          string            // globally unique tombstone ID; MUST use prefix "tomb_"
                                 //   followed by a UUID v7 (time-ordered) suffix
  entity_uri:  string            // URI of the entity being tombstoned (e.g. "user:alice")
  scope:       ScopePattern      // which scope(s) this tombstone covers (§23.2.3)
  reason:      string | null     // operator-supplied reason; SHOULD be provided; MAY be
                                 //   redacted to "redacted" before forwarding to federation
                                 //   peers when the reason contains PII or legal detail
  signed_by:   string            // URI of the admin agent or service that signed the tombstone
  key_id:      string            // SHA-256 hex of the signing key (§19.1.2); REQUIRED; included
                                 //   in the signed canonical body so verifiers can resolve the
                                 //   correct historical key after rotation without trial-verification
  signature:   string            // base64url Ed25519 signature over the canonical-JSON body
                                 //   of this record, with "signature" and "reason" excluded
                                 //   before JCS canonicalization (§23.2.4)
  created_at:  ISO 8601 string   // timestamp when the tombstone was issued
  legal_hold:  boolean           // default false; see §24.3
```

#### §23.2.2 Invariants {#section-23-2-2}

1. `id` MUST be globally unique and MUST be issued with the `"tomb_"` prefix followed by a UUID v7 (time-ordered) suffix.
2. `entity_uri` MUST conform to the URI format defined in §9 (Namespace Registry). Wildcards MUST NOT be used in `entity_uri`; each tombstone covers exactly one entity URI.
3. `signed_by` MUST identify an agent or service that holds an active admin API key at the time of tombstone issuance. The `signature` MUST be verifiable against the signing key in the org manifest (§19.1).
4. Tombstone records MUST be stored in a dedicated `tombstones` table (§23.5.3) that is separate from the `facts` table. Tombstones MUST NOT be stored as ordinary facts.
5. Tombstone records are immutable once written. Operators MUST NOT update or delete a tombstone record. To reinstate a tombstoned entity, a separate `TombstoneRevocation` record (§23.2.5) MUST be issued.

#### §23.2.3 Scope Pattern {#section-23-2-3}

`ScopePattern` controls which scopes of facts the tombstone suppresses:

| Value | Meaning |
|---|---|
| `"*"` | All scopes (`local`, `team`, `company`, `public`) |
| `"local"` | Local scope only |
| `"team"` | Team scope only |
| `"company"` | Company scope only |
| `"public"` | Public scope only |
| Array of the above strings | Union of listed scopes |

A tombstone with `scope: "*"` is the broadest possible suppression. Operators SHOULD use the narrowest scope that satisfies the RTBF obligation.

#### §23.2.4 Canonical JSON for Signing {#section-23-2-4}

The canonical-JSON body for signature computation MUST be produced using RFC 8785 (JCS — JSON Canonicalization Scheme) over the `TombstoneRecord` object with the `"signature"` and `"reason"` fields **excluded** from the object before canonicalization (consistent with the field-exclusion pattern in §19.1.3). The `signed_by` value MUST be the plain string URI, not a reference.

Excluding `"reason"` from the signed body allows the issuing node to redact it to `"redacted"` before federation rebroadcast (§23.4.1.3) without invalidating the signature on peer nodes. Excluding `"signature"` avoids self-reference. Both exclusions MUST be applied before JCS serialization; implementations MUST NOT use empty-string sentinels in place of exclusion.

The `"key_id"` field MUST be included in the signed canonical body so that verifiers can resolve the correct historical signing key without trial-verifying against the entire rotation chain (see §19.1.4).

#### §23.2.5 Tombstone Revocation {#section-23-2-5}

A tombstone may be revoked by an admin who has a documented legal basis (e.g.,
a legal hold set by court order). Revocation is expressed via a separate
`TombstoneRevocation` record rather than deleting the tombstone, because
tombstone records are immutable — the revocation creates an auditable
counterpart that references the original tombstone ID. Both records are
retained indefinitely for compliance evidence.

```
TombstoneRevocationRecord:
  id:            string   // "tombrevoke_" + UUID v7
  tombstone_id:  string   // the "tomb_" record being revoked
  reason:        string   // MUST be provided (e.g., court order reference)
  signed_by:     string
  signature:     string
  created_at:    ISO 8601 string
```

A revocation does NOT delete the tombstone record. It instructs nodes to re-expose facts that were suppressed solely by the revoked tombstone. Revocations are subject to the same signature and federation propagation rules as tombstones (§23.4).

### §23.3 Recall-Time Tombstone Filter {#section-23-3}

#### §23.3.1 Direct-Entity Suppression {#section-23-3-1}

At recall time, before returning any fact or memory card to the caller, the node MUST:

1. Resolve the set of active tombstones for every `entity_uri` that appears in the candidate result set (as the `entity` field, or as a value of type `ref`).
2. Exclude any fact whose `entity` matches a tombstoned `entity_uri` where the tombstone `scope` covers the fact's `scope`.
3. Exclude any memory card (§20.4) whose `about_entity` matches a tombstoned entity under the same scope rule.

A tombstone is **active** if it is present in the `tombstones` table and has no corresponding `tombstone_id` entry in the `tombstone_revocations` table.

#### §23.3.2 Graph Reference Suppression {#section-23-3-2}

The tombstone filter MUST also suppress indirect graph references to tombstoned entities:

1. During graph traversal (k-hop, §20.1), edges that reference a tombstoned entity as the `target_entity_uri` MUST be excluded from the traversal result. The traversal MUST NOT propagate through tombstoned nodes. (Note: edges where the tombstoned entity is the *source* are suppressed by §23.3.1 step 2, which excludes all facts whose `entity` is tombstoned.)
2. Facts whose `value` is of type `ref` and whose ref value matches a tombstoned `entity_uri` MUST be excluded from recall results.
3. Memory cards in the candidate set MUST be handled as follows. A card whose `about_entity` is tombstoned MUST be suppressed entirely — it MUST NOT appear in the response. A card where the tombstoned entity appears only in `related_entities` MUST have that entry omitted from `related_entities`; if after omission the card's text body still contains PII attributed to the tombstoned entity, the card MUST also be suppressed. Implementations SHOULD regenerate or suppress cards synthesized from tombstoned fact sets rather than returning stale or partially-pruned text bodies.
4. Facts returned in recall or provenance walk results that have `derived_from` entries referencing tombstoned entities MUST represent those entries as `{"hash": "...", "exists": false}` — identical to the unauthorized cross-scope pattern defined in §20.6.2.

#### §23.3.3 Completeness and Consistency {#section-23-3-3}

1. The tombstone check MUST be applied after scope filtering and before token-budget packing.
2. The tombstone check MUST be applied to `GET /v1/recall` (§20.3), `recall_instruction` responses (§21.3), and subscription event delivery (§20.5.5). For subscription delivery, the tombstone filter MUST be re-evaluated immediately before populating event content at delivery time — the delivery-time check in §20.5.5 MUST be extended to include a tombstone lookup in addition to the existing garden ACL and token revocation checks.
3. Implementations MUST NOT return a count, aggregate, or embedding that reveals the existence of suppressed facts. A result set that would have included tombstoned facts MUST be indistinguishable (from the caller's perspective) from a result set that never contained such facts. Pagination total counts and any other response fields that reflect the pre-filter cardinality of the result set MUST be computed on the post-tombstone-filter set only. HTTP response headers (e.g., `X-Total-Count`) MUST NOT reflect suppressed facts.
4. Implementations MUST cache active tombstone IDs in an in-process LRU cache and refresh it at most every **60 seconds**. A tombstone issued on the local node MUST be effective within 60 seconds. Federation propagation latency may extend this window for peer nodes; see §23.4.
5. Tombstone lookups for both live and `as_of` queries MUST be performed such that tombstone visibility is consistent within the query's execution scope. Implementations using SQLite MUST use `BEGIN IMMEDIATE` for tombstone reads concurrent with query execution. PostgreSQL implementations MUST use at minimum `READ COMMITTED` with tombstone reads issued after the query plan is complete, ensuring that tombstones committed before the read are visible.

### §23.4 Federation Propagation {#section-23-4}

#### §23.4.1 Outbound Rebroadcast {#section-23-4-1}

1. When a node issues a new `TombstoneRecord`, it MUST enqueue the tombstone for replication to all active federation peers under the existing federation protocol (§6).
2. The tombstone MUST be replicated with the `signed_by` and `signature` fields unchanged. Peer nodes MUST NOT re-sign tombstones; they MUST verify the original signature before applying the tombstone locally.
3. The `reason` field MAY be redacted to `"redacted"` by the issuing node before rebroadcast, at the operator's discretion. Peer nodes MUST NOT require a non-`"redacted"` reason to accept the tombstone.

#### §23.4.2 Inbound Tombstone Handling {#section-23-4-2}

On receiving an inbound tombstone from a federation peer, the node MUST:

1. Verify the `signature` against the public key published in the org manifest for the entity URI identified by `signed_by`. Nodes MUST resolve the `signed_by` URI to an org manifest via the transparency log or `/.well-known/stigmem-manifest.json`, independent of which peer forwarded the tombstone. Resolving the relaying peer's manifest instead of the `signed_by` manifest is a protocol error. Use `key_id` (§23.2.1) to select the correct historical key from the resolved manifest's rotation chain.
2. Verify the `created_at` timestamp is not older than the node's configured retention horizon. The ±5-minute replay-protection window defined in §22.5 applies to session/handshake nonces, not to persistent tombstone records. Tombstones are durable records whose `created_at` is inherently in the past; applying the §22.5 window would permanently reject any tombstone that arrives more than 5 minutes after issuance (e.g., due to peer downtime or federation delay). Replay prevention for the tombstone delivery request itself is handled by the federation connection nonce (§22.5) — it does not need to be re-applied to the data payload's `created_at`.
3. Write the tombstone to the local `tombstones` table if it does not already exist (idempotent on `id`).
4. Apply the recall-time filter within 60 seconds for the tombstoned entity.

Nodes MUST NOT silently drop inbound tombstones. If tombstone verification fails, the node MUST emit a `tombstone_verification_failed` audit log event (§22.3) and SHOULD alert the operator.

Nodes MUST accept tombstones from any trusted federation peer (peers listed in the local org manifest's `trusted_peers`), not only from the org that first issued the tombstone.

#### §23.4.3 Tombstone Federation Route {#section-23-4-3}

Tombstones are exchanged via a dedicated federation route, separate from the
fact replication path (§5.8). This separation ensures that tombstones can be
propagated even when fact replication is paused or throttled. The route returns
both tombstone records and revocation records in a single paginated response so
that peers can apply both in a single pass.

```
GET /v1/federation/tombstones?since=<ISO8601>&limit=<N>
Authorization: Bearer <peer capability token>

→ 200 {
    "tombstones":  [ ...TombstoneRecord... ],
    "revocations": [ ...TombstoneRevocationRecord... ],
    "cursor":      "<opaque pagination cursor>"
  }
→ 401 if capability token invalid or scope insufficient
```

The peer capability token (§19.3) MUST include the `"tombstone:read"` verb in its `verbs` array. Peers MUST poll this route at least every **5 minutes** in standard federation mode, and MUST poll within **60 seconds** of receiving a `tombstone_new` event via the subscription channel (§20.5).

### §23.5 Storage-Trait Extension {#section-23-5}

#### §23.5.1 New Methods {#section-23-5-1}

The following methods MUST be added to the storage trait. `tombstone()` creates
a tombstone record, `is_tombstoned()` is the hot-path check called at recall
time, `list_tombstones()` supports the federation replication and admin
inspection endpoints, and `revoke_tombstone()` lifts a suppression when a legal
basis exists.

```
tombstone(
  entity_uri: string,
  scope:      ScopePattern,
  reason:     string | null,
  signed_by:  string,
  signature:  string,
  legal_hold: bool
) → TombstoneRecord

is_tombstoned(
  entity_uri: string,
  scope:      FactScope       // the scope of the fact being checked
) → bool

list_tombstones(
  scope:  ScopePattern | null,  // null = all
  since:  ISO8601 | null
) → [TombstoneRecord]

revoke_tombstone(
  tombstone_id: string,
  reason:       string,
  signed_by:    string,
  signature:    string
) → TombstoneRevocationRecord
```

#### §23.5.2 Semantics {#section-23-5-2}

1. `tombstone(...)` MUST be idempotent: calling it with the same `entity_uri` and `scope` when a matching active tombstone already exists MUST return the existing tombstone without writing a new record.
2. `is_tombstoned(entity_uri, scope)` MUST return `true` if any active tombstone covers `entity_uri` with a `ScopePattern` that includes the given `FactScope`. Implementations SHOULD cache this check (see §23.3.3 rule 4).
3. `revoke_tombstone(...)` MUST fail with `tombstone_not_found` if no matching tombstone exists, and MUST fail with `tombstone_already_revoked` if a revocation record already exists for that tombstone.

#### §23.5.3 Schema Migration {#section-23-5-3}

Migration 013a adds the `tombstones` and `tombstone_revocations` tables.
Tombstones are indexed by `entity_uri` for the hot-path `is_tombstoned()`
lookup. Migration 013c adds the `fact_retractions` table, an append-only log
of retraction events needed by time-travel queries (§24) — existing retraction
semantics (setting `facts.confidence = 0.0`) remain unchanged, but all
retraction writes MUST also insert into this log so that `as_of` queries can
reconstruct the knowledge graph at a past point in time.

```sql
-- Migration 013a: RTBF tombstones
CREATE TABLE tombstones (
  id          TEXT PRIMARY KEY,          -- "tomb_" + UUIDv7
  entity_uri  TEXT NOT NULL,
  scope       TEXT NOT NULL,             -- serialized ScopePattern JSON
  reason      TEXT,
  signed_by   TEXT NOT NULL,
  signature   TEXT NOT NULL,
  created_at  TEXT NOT NULL,             -- ISO 8601
  legal_hold  INTEGER NOT NULL DEFAULT 0 -- 0 = false, 1 = true
);

CREATE INDEX idx_tombstones_entity_uri ON tombstones(entity_uri);

CREATE TABLE tombstone_revocations (
  id           TEXT PRIMARY KEY,         -- "tombrevoke_" + UUIDv7
  tombstone_id TEXT NOT NULL REFERENCES tombstones(id),
  reason       TEXT NOT NULL,
  signed_by    TEXT NOT NULL,
  signature    TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
```

A separate migration adds the retraction log table required by time-travel queries (§24). Retractions in the base schema set `facts.confidence = 0.0` in place, which destroys the temporal record. The `fact_retractions` table preserves the retraction timestamp and actor so that `as_of` queries can reconstruct which facts were live at any historical point.

```sql
-- Migration 013c: append-only retraction log (time-travel compat — §24.2.1 c.3)
-- Retraction writes MUST insert here in addition to setting facts.confidence = 0.0.
CREATE TABLE fact_retractions (
  id           TEXT PRIMARY KEY,    -- "retract_" + UUIDv7
  fact_id      TEXT NOT NULL REFERENCES facts(id),
  retracted_at TEXT NOT NULL,       -- ISO 8601; authoritative timestamp for as_of queries
  retracted_by TEXT                 -- actor entity URI if known
);

CREATE INDEX idx_fact_retractions_fact_id ON fact_retractions(fact_id);
CREATE INDEX idx_fact_retractions_retracted_at ON fact_retractions(retracted_at);
```

### §23.6 Wire Format {#section-23-6}

#### §23.6.1 Issue a Tombstone {#section-23-6-1}

Creates a new tombstone for the specified entity. The server signs the record
with the node's active admin signing key before returning it. Only admin API
keys may call this endpoint — agent keys are rejected with 403 because
tombstone issuance is an administrative action with compliance implications.

```
POST /v1/tombstones
Authorization: Bearer <admin api-key>
Content-Type: application/json

{
  "entity_uri": "user:alice",
  "scope":      "*",
  "reason":     "GDPR Art. 17 erasure request #2026-042",
  "legal_hold": false
}
→ 201 { ...TombstoneRecord with id, signature, created_at populated... }
→ 400 tombstone_invalid_scope      if scope value is not a valid ScopePattern
→ 400 tombstone_entity_uri_invalid if entity_uri does not conform to §9 namespace format
→ 403 if caller is not an admin API key
→ 409 tombstone_already_exists     if an active tombstone for this entity_uri + scope exists
```

The server MUST sign the tombstone with the node's active admin signing key before returning.

#### §23.6.2 Check Tombstone Status {#section-23-6-2}

Returns the tombstone status for a given entity URI. The response indicates
whether the entity is currently tombstoned and includes all tombstone and
revocation records for audit. This endpoint is admin-only because the existence
of a tombstone for a specific entity is itself sensitive information that could
reveal the identity of a data-erasure requester.

```
GET /v1/tombstones/:entity_uri_encoded
Authorization: Bearer <admin api-key>

→ 200 { "tombstoned": true,  "tombstones": [...TombstoneRecord...], "revocations": [...] }
→ 200 { "tombstoned": false, "tombstones": [] }
→ 403 if caller is not an admin API key
```

This endpoint MUST NOT be accessible with agent API keys — the existence of a tombstone for a given entity is itself sensitive information.

#### §23.6.3 Revoke a Tombstone {#section-23-6-3}

Revokes an active tombstone, reinstating the suppressed entity's facts in
future recall responses. The caller MUST provide a documented reason (e.g., a
court order reference) because revocations have compliance implications — the
`reason` field is required (not optional) for this endpoint. The node signs
the revocation record and propagates it to federation peers alongside future
tombstone replication.

```
POST /v1/tombstones/:tombstone_id/revoke
Authorization: Bearer <admin api-key>
Content-Type: application/json

{ "reason": "Court order #2026-CR-1234 reinstating data access" }

→ 200 { ...TombstoneRevocationRecord... }
→ 403 if caller is not an admin API key
→ 404 tombstone_not_found
→ 409 tombstone_already_revoked
```

### §23.7 Error Reference {#section-23-7}

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `tombstone_invalid_scope` | `scope` value is not a valid ScopePattern |
| 400 | `tombstone_entity_uri_invalid` | `entity_uri` does not conform to §9 namespace format |
| 400 | `tombstone_verification_failed` | Signature verification failed on inbound federation tombstone |
| 403 | `tombstone_access_denied` | Agent API key used on tombstone endpoint; admin key required |
| 404 | `tombstone_not_found` | Tombstone ID not found |
| 409 | `tombstone_already_exists` | Active tombstone for this entity_uri + scope already exists |
| 409 | `tombstone_already_revoked` | Tombstone has already been revoked |

---

## Subsection anchors {#subsection-anchors}

*Anchors below are provided so docs links to specific subsections always resolve, even when the subsection text lives only in earlier spec drafts.*

### §23.4.1.3 {#section-23-4-1-3}
