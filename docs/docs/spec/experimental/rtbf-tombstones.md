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

<p className="stigmem-meta"><span>7 min read</span><span>Spec contributor · Compliance reviewer</span><span>Experimental · v0.9.0bN</span></p>

<div className="stigmem-lead">

**What this section covers**

Cryptographic tombstones, recall-time suppression, federation
propagation, and legal-hold mode. A tombstone is a signed, durable
record that directs every node in the federation to suppress facts
about a specified entity from all future recall responses.

</div>

**Status:** Experimental / opt-in source package on `main`

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

This section defines the tombstone mechanism for compliance with right-to-be-forgotten (RTBF) obligations under data-protection frameworks (e.g., GDPR Art. 17, CCPA §1798.105).

<div className="stigmem-keypoint">

**Tombstones are a protocol primitive, not a legal determination.**

Operators MUST obtain appropriate legal guidance before issuing or
refusing tombstone requests.

</div>

### §23.2 Tombstone Record Shape {#section-23-2}

#### §23.2.1 Schema {#section-23-2-1}

A tombstone record is a self-contained, cryptographically signed directive. It identifies the target entity, the scopes to suppress, and the admin who authorised the erasure. The `signature` field covers the canonical JSON of all other fields (except `reason`, which is excluded to allow redaction during federation rebroadcast).

```
TombstoneRecord:
  id:          string            // globally unique tombstone ID; MUST use prefix "tomb_"
                                 //   followed by a UUID v7 (time-ordered) suffix
  entity_uri:  string            // URI of the entity being tombstoned
  scope:       ScopePattern      // which scope(s) this tombstone covers
  reason:      string | null     // operator-supplied reason; MAY be redacted to "redacted"
                                 //   before forwarding to federation peers
  signed_by:   string            // URI of the admin agent or service that signed the tombstone
  key_id:      string            // SHA-256 hex of the signing key; REQUIRED
  signature:   string            // base64url Ed25519 signature over canonical-JSON body
                                 //   (with "signature" and "reason" excluded)
  created_at:  ISO 8601 string
  legal_hold:  boolean           // default false; see §24.3
```

#### §23.2.2 Invariants {#section-23-2-2}

<ol className="stigmem-steps">
<li><code>id</code> MUST be globally unique and MUST use the <code>"tomb_"</code> prefix followed by a UUID v7 (time-ordered) suffix.</li>
<li><code>entity_uri</code> MUST conform to the URI format defined in §9. Wildcards MUST NOT be used; each tombstone covers exactly one entity URI.</li>
<li><code>signed_by</code> MUST identify an agent or service that holds an active admin API key at the time of tombstone issuance. The <code>signature</code> MUST be verifiable against the signing key in the org manifest.</li>
<li>Tombstone records MUST be stored in a dedicated <code>tombstones</code> table separate from the <code>facts</code> table. Tombstones MUST NOT be stored as ordinary facts.</li>
<li>Tombstone records are immutable once written. To reinstate a tombstoned entity, a separate <code>TombstoneRevocation</code> record MUST be issued.</li>
</ol>

#### §23.2.3 Scope Pattern {#section-23-2-3}

`ScopePattern` controls which scopes of facts the tombstone suppresses:

<div className="stigmem-fields">

<div>
<dt>Value</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>"&#42;"</code></dt>
<dt><span className="stigmem-fields__type">all scopes</span></dt>
<dd>All scopes (<code>local</code>, <code>team</code>, <code>company</code>, <code>public</code>).</dd>
</div>

<div>
<dt><code>"local"</code> / <code>"team"</code> / <code>"company"</code> / <code>"public"</code></dt>
<dt><span className="stigmem-fields__type">single</span></dt>
<dd>That scope only.</dd>
</div>

<div>
<dt>Array</dt>
<dt><span className="stigmem-fields__type">union</span></dt>
<dd>Union of listed scopes.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Operators SHOULD use the narrowest scope that satisfies the RTBF obligation.**

A tombstone with `scope: "*"` is the broadest possible suppression.

</div>

#### §23.2.4 Canonical JSON for Signing {#section-23-2-4}

The canonical-JSON body for signature computation MUST be produced using RFC 8785 (JCS — JSON Canonicalization Scheme) over the `TombstoneRecord` object with the `"signature"` and `"reason"` fields **excluded** from the object before canonicalization (consistent with the field-exclusion pattern in §19.1.3). The `signed_by` value MUST be the plain string URI, not a reference.

Excluding `"reason"` from the signed body allows the issuing node to redact it to `"redacted"` before federation rebroadcast without invalidating the signature on peer nodes. Excluding `"signature"` avoids self-reference. Both exclusions MUST be applied before JCS serialization; implementations MUST NOT use empty-string sentinels in place of exclusion.

The `"key_id"` field MUST be included in the signed canonical body so that verifiers can resolve the correct historical signing key without trial-verifying against the entire rotation chain.

#### §23.2.5 Tombstone Revocation {#section-23-2-5}

A tombstone may be revoked by an admin who has a documented legal basis. Revocation is expressed via a separate `TombstoneRevocation` record rather than deleting the tombstone, because tombstone records are immutable.

```
TombstoneRevocationRecord:
  id:            string   // "tombrevoke_" + UUID v7
  tombstone_id:  string   // the "tomb_" record being revoked
  reason:        string   // MUST be provided (e.g., court order reference)
  signed_by:     string
  signature:     string
  created_at:    ISO 8601 string
```

<div className="stigmem-keypoint">

**A revocation does NOT delete the tombstone record.**

It instructs nodes to re-expose facts that were suppressed solely by
the revoked tombstone. Both records are retained indefinitely for
compliance evidence.

</div>

### §23.3 Recall-Time Tombstone Filter {#section-23-3}

#### §23.3.1 Direct-Entity Suppression {#section-23-3-1}

At recall time, before returning any fact or memory card to the caller, the node MUST:

<ol className="stigmem-steps">
<li>Resolve the set of active tombstones for every <code>entity_uri</code> that appears in the candidate result set (as the <code>entity</code> field, or as a value of type <code>ref</code>).</li>
<li>Exclude any fact whose <code>entity</code> matches a tombstoned <code>entity_uri</code> where the tombstone <code>scope</code> covers the fact's <code>scope</code>.</li>
<li>Exclude any memory card whose <code>about_entity</code> matches a tombstoned entity under the same scope rule.</li>
</ol>

A tombstone is **active** if it is present in the `tombstones` table and has no corresponding `tombstone_id` entry in the `tombstone_revocations` table.

#### §23.3.2 Graph Reference Suppression {#section-23-3-2}

The tombstone filter MUST also suppress indirect graph references to tombstoned entities:

<ol className="stigmem-steps">
<li>During graph traversal (k-hop, §20.1), edges that reference a tombstoned entity as the <code>target_entity_uri</code> MUST be excluded. The traversal MUST NOT propagate through tombstoned nodes.</li>
<li>Facts whose <code>value</code> is of type <code>ref</code> and whose ref value matches a tombstoned <code>entity_uri</code> MUST be excluded.</li>
<li>Memory cards in the candidate set: a card whose <code>about_entity</code> is tombstoned MUST be suppressed entirely. A card where the tombstoned entity appears only in <code>related_entities</code> MUST have that entry omitted; if the text body still contains PII attributed to the tombstoned entity, the card MUST also be suppressed.</li>
<li>Facts with <code>derived_from</code> entries referencing tombstoned entities MUST represent those entries as <code>&#123;"hash": "...", "exists": false&#125;</code>.</li>
</ol>

#### §23.3.3 Completeness and Consistency {#section-23-3-3}

<div className="stigmem-keypoint">

**A result set that would have included tombstoned facts MUST be indistinguishable from one that never contained them.**

No count, aggregate, or embedding may reveal the existence of
suppressed facts. Pagination totals and `X-Total-Count` headers MUST
be computed on the post-tombstone-filter set only.

</div>

<div className="stigmem-grid">

<div><h4>After scope, before packing</h4><p>The tombstone check MUST be applied after scope filtering and before token-budget packing.</p></div>
<div><h4>All recall paths</h4><p>Applies to <code>GET /v1/recall</code>, <code>recall_instruction</code>, and subscription event delivery.</p></div>
<div><h4>60 s LRU refresh</h4><p>Implementations MUST cache active tombstone IDs in an in-process LRU and refresh at most every 60 seconds.</p></div>
<div><h4>SQLite / PG isolation</h4><p>SQLite MUST use <code>BEGIN IMMEDIATE</code>; PostgreSQL MUST use at minimum <code>READ COMMITTED</code> with tombstone reads issued after the query plan is complete.</p></div>

</div>

### §23.4 Federation Propagation {#section-23-4}

#### §23.4.1 Outbound Rebroadcast {#section-23-4-1}

<ol className="stigmem-steps">
<li>When a node issues a new <code>TombstoneRecord</code>, it MUST enqueue the tombstone for replication to all active federation peers under the existing federation protocol.</li>
<li>The tombstone MUST be replicated with the <code>signed_by</code> and <code>signature</code> fields unchanged. Peer nodes MUST NOT re-sign tombstones; they MUST verify the original signature before applying the tombstone locally.</li>
<li>The <code>reason</code> field MAY be redacted to <code>"redacted"</code> by the issuing node before rebroadcast. Peer nodes MUST NOT require a non-<code>"redacted"</code> reason to accept the tombstone.</li>
</ol>

#### §23.4.2 Inbound Tombstone Handling {#section-23-4-2}

On receiving an inbound tombstone from a federation peer, the node MUST:

<ol className="stigmem-steps">
<li>Verify the <code>signature</code> against the public key published in the org manifest for the entity URI identified by <code>signed_by</code>. Resolving the relaying peer's manifest instead of the <code>signed_by</code> manifest is a protocol error. Use <code>key_id</code> to select the correct historical key from the rotation chain.</li>
<li>Verify the <code>created_at</code> timestamp is not older than the node's configured retention horizon. The ±5-minute replay-protection window from §22.5 does NOT apply to persistent tombstone records — they are durable records whose <code>created_at</code> is inherently in the past.</li>
<li>Write the tombstone to the local <code>tombstones</code> table if it does not already exist (idempotent on <code>id</code>).</li>
<li>Apply the recall-time filter within 60 seconds for the tombstoned entity.</li>
</ol>

<div className="stigmem-keypoint">

**Nodes MUST NOT silently drop inbound tombstones.**

If tombstone verification fails, the node MUST emit a
`tombstone_verification_failed` audit log event and SHOULD alert the
operator. Nodes MUST accept tombstones from any trusted federation
peer, not only from the org that first issued the tombstone.

</div>

#### §23.4.3 Tombstone Federation Route {#section-23-4-3}

Tombstones are exchanged via a dedicated federation route, separate from the fact replication path. This separation ensures that tombstones can be propagated even when fact replication is paused or throttled.

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

The peer capability token MUST include the `"tombstone:read"` verb in its `verbs` array. Peers MUST poll this route at least every **5 minutes** in standard federation mode, and MUST poll within **60 seconds** of receiving a `tombstone_new` event via the subscription channel.

### §23.5 Storage-Trait Extension {#section-23-5}

#### §23.5.1 New Methods {#section-23-5-1}

```
tombstone(entity_uri, scope, reason, signed_by, signature, legal_hold) → TombstoneRecord
is_tombstoned(entity_uri, scope) → bool
list_tombstones(scope, since) → [TombstoneRecord]
revoke_tombstone(tombstone_id, reason, signed_by, signature) → TombstoneRevocationRecord
```

#### §23.5.2 Semantics {#section-23-5-2}

<div className="stigmem-grid">

<div><h4>Idempotent tombstone()</h4><p>Calling with the same <code>entity_uri</code> and <code>scope</code> when a matching active tombstone exists MUST return the existing tombstone without writing a new record.</p></div>
<div><h4>Cached is_tombstoned()</h4><p>Returns <code>true</code> if any active tombstone covers <code>entity_uri</code> with a <code>ScopePattern</code> that includes the given <code>FactScope</code>. SHOULD be cached per §23.3.3.</p></div>
<div><h4>Revoke failures</h4><p><code>revoke_tombstone()</code> MUST fail with <code>tombstone_not_found</code> if no matching tombstone exists, and <code>tombstone_already_revoked</code> if a revocation already exists.</p></div>

</div>

#### §23.5.3 Schema Migration {#section-23-5-3}

Migration 013a adds the `tombstones` and `tombstone_revocations` tables. Tombstones are indexed by `entity_uri` for the hot-path `is_tombstoned()` lookup. Migration 013c adds the `fact_retractions` table, an append-only log of retraction events needed by time-travel queries (§24).

```sql
-- Migration 013a: RTBF tombstones
CREATE TABLE tombstones (
  id          TEXT PRIMARY KEY,
  entity_uri  TEXT NOT NULL,
  scope       TEXT NOT NULL,
  reason      TEXT,
  signed_by   TEXT NOT NULL,
  signature   TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  legal_hold  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_tombstones_entity_uri ON tombstones(entity_uri);

CREATE TABLE tombstone_revocations (
  id           TEXT PRIMARY KEY,
  tombstone_id TEXT NOT NULL REFERENCES tombstones(id),
  reason       TEXT NOT NULL,
  signed_by    TEXT NOT NULL,
  signature    TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
```

```sql
-- Migration 013c: append-only retraction log (time-travel compat — §24.2.1 c.3)
CREATE TABLE fact_retractions (
  id           TEXT PRIMARY KEY,
  fact_id      TEXT NOT NULL REFERENCES facts(id),
  retracted_at TEXT NOT NULL,
  retracted_by TEXT
);

CREATE INDEX idx_fact_retractions_fact_id ON fact_retractions(fact_id);
CREATE INDEX idx_fact_retractions_retracted_at ON fact_retractions(retracted_at);
```

### §23.6 Wire Format {#section-23-6}

#### §23.6.1 Issue a Tombstone {#section-23-6-1}

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
→ 400 tombstone_invalid_scope
→ 400 tombstone_entity_uri_invalid
→ 403 if caller is not an admin API key
→ 409 tombstone_already_exists
```

#### §23.6.2 Check Tombstone Status {#section-23-6-2}

<div className="stigmem-keypoint">

**This endpoint MUST NOT be accessible with agent API keys.**

The existence of a tombstone for a given entity is itself sensitive
information that could reveal the identity of a data-erasure
requester.

</div>

```
GET /v1/tombstones/:entity_uri_encoded
Authorization: Bearer <admin api-key>

→ 200 { "tombstoned": true,  "tombstones": [...TombstoneRecord...], "revocations": [...] }
→ 200 { "tombstoned": false, "tombstones": [] }
→ 403 if caller is not an admin API key
```

#### §23.6.3 Revoke a Tombstone {#section-23-6-3}

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

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Error code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>tombstone_invalid_scope</code></span></dt>
<dd><code>scope</code> value is not a valid ScopePattern.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>tombstone_entity_uri_invalid</code></span></dt>
<dd><code>entity_uri</code> does not conform to §9 namespace format.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>tombstone_verification_failed</code></span></dt>
<dd>Signature verification failed on inbound federation tombstone.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type"><code>tombstone_access_denied</code></span></dt>
<dd>Agent API key used on tombstone endpoint; admin key required.</dd>
</div>

<div>
<dt>404</dt>
<dt><span className="stigmem-fields__type"><code>tombstone_not_found</code></span></dt>
<dd>Tombstone ID not found.</dd>
</div>

<div>
<dt>409</dt>
<dt><span className="stigmem-fields__type"><code>tombstone_already_exists</code></span></dt>
<dd>Active tombstone for this entity_uri + scope already exists.</dd>
</div>

<div>
<dt>409</dt>
<dt><span className="stigmem-fields__type"><code>tombstone_already_revoked</code></span></dt>
<dd>Tombstone has already been revoked.</dd>
</div>

</div>

---

## Subsection anchors {#subsection-anchors}

*Anchors below are provided so docs links to specific subsections always resolve, even when the subsection text lives only in earlier spec drafts.*

### §23.4.1.3 {#section-23-4-1-3}
