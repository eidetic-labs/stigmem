---
spec_id: Spec-X3-Time-Travel-Queries
version: 0.1.0-alpha.0
status: Experimental
applies_to: v0.9.0a4 alpha plugin-validation line
last_updated: 2026-05-22
supersedes: pre-reset §24 time-travel/as-of query material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-X2-RTBF-Tombstones >= 0.1.0-alpha.0
title: §24. Time-Travel / As-Of Queries
sidebar_label: §24 Time-Travel / As-Of Queries
audience: Spec
description: "Stigmem spec section 24 — as_of parameter on /v1/recall and /v1/facts; append-only retraction log."
stability: experimental
since: 0.9.0a1
---

# §24. Time-Travel / As-Of Queries {#section-24}

<p className="stigmem-meta"><span>6 min read</span><span>Spec contributor · Compliance reviewer</span><span>Experimental · v0.9.0a4 plugin validation</span></p>

<div className="stigmem-lead">

**What this section covers**

The `as_of` parameter on `/v1/recall` and `/v1/facts` plus the
append-only retraction log. Historical auditing, debugging,
regulatory compliance reporting, and causal provenance
reconstruction.

</div>

**Status:** Experimental / opt-in source package on `main`

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for time-travel query semantics.

:::caution EXPERIMENTAL
Time-travel semantics interact with tombstones in ways that are still being finalized. Specifically:

- The default install rejects `as_of` requests unless
  `stigmem-plugin-time-travel` is registered and the relevant fact-query or
  recall operator gate is enabled. This source package is available for alpha
  validation on `main`, but signed/package artifact evidence is deferred until
  the plugin release train is opened.
- The a4 read path validates retroactive tombstone suppression and non-admin
  legal-hold silence. Broader RTBF tombstone launch, federation authority, and
  operator runbooks remain outside the a4 time-travel release.
- Isolation guarantees differ between SQLite (`BEGIN IMMEDIATE`) and PostgreSQL (`READ COMMITTED`). Test your workload on the production backend before going live.
- `legal_hold` historical access requires an admin path; operator key
  separation and audit runbooks are not yet complete.
:::

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** Experimental. §24.1–§24.6 preserve proposed MUST/SHOULD/MAY language for ADR-008 review, but they are not part of the supported default install.

### §24.1 Scope {#section-24-1}

Time-travel queries allow callers to retrieve the state of the knowledge graph at a past point in time. This enables historical auditing, debugging, regulatory compliance reporting, and causal provenance reconstruction.

The `as_of` parameter is an ISO 8601 timestamp specifying the point-in-time to query. An `as_of` query returns facts as they were visible to an ordinary query at that timestamp, subject to tombstone interaction rules (§24.3).

### §24.2 As-Of Query Semantics {#section-24-2}

#### §24.2.1 Fact Visibility at Time T {#section-24-2-1}

A fact `f` is **visible at time T** if all of the following conditions hold:

<ol className="stigmem-steps">
<li><code>f.created_at &lt;= T</code> — the fact had been written before or at T.</li>
<li><code>f.valid_until is null OR f.valid_until &gt; T</code> — the fact had not yet expired at T.</li>
<li><code>f.confidence &gt; 0 at time T</code> — the fact had not been retracted by T. Retraction is governed by the <code>fact_retractions</code> append-only log (see §23.5.3 Migration 013c). A fact is considered retracted at T if and only if a row exists in <code>fact_retractions</code> with <code>fact_id = f.id</code> and <code>retracted_at &lt;= T</code>. The in-place <code>confidence=0.0</code> on the <code>facts</code> row is used for live queries only; <code>query_facts_as_of</code> MUST join <code>fact_retractions</code> and MUST NOT use the <code>facts.confidence</code> field as a proxy for retraction state at historical timestamps.</li>
<li>No active tombstone (§23.3) covers <code>f.entity</code> with a scope matching <code>f.scope</code>, unless the tombstone has <code>legal_hold: true</code> (§24.3).</li>
</ol>

<div className="stigmem-keypoint">

**Tombstone suppression is retroactive.**

The fact-visibility definition at time T is not a purely historical
snapshot — it reflects present tombstone state. Callers MUST NOT
assume that a result set for `as_of=T` is immutable; a subsequently
issued tombstone will retroactively change it.

</div>

#### §24.2.2 Query Interface {#section-24-2-2}

The `as_of` parameter MUST be accepted on the following endpoints:

```
GET  /v1/recall?intent=<string>&as_of=<ISO8601>&...
POST /v1/recall   { "intent": "...", "as_of": "2025-01-01T00:00:00Z", ... }
GET  /v1/facts?entity_uri=<string>&as_of=<ISO8601>&...
```

The `as_of` timestamp MUST be validated as:

<div className="stigmem-grid">

<div><h4>Valid ISO 8601</h4></div>
<div><h4>Not in the future</h4><p>At most server clock + 5 s tolerance for skew.</p></div>
<div><h4>Within retention horizon</h4><p>Operators MAY configure a minimum <code>as_of</code> floor; queries before the floor MUST return <code>as_of_before_retention_floor</code>.</p></div>

</div>

#### §24.2.3 Monotonicity Invariant {#section-24-2-3}

<div className="stigmem-keypoint">

**The `as_of` result set MUST be monotonically consistent.**

For any two queries with `as_of=T1 < T2`, the set of facts visible
at T1 MUST be a subset of the facts visible at T2, before accounting
for tombstones, retraction, or expiry. This invariant allows callers
to reason about the causal evolution of the knowledge graph.

</div>

### §24.3 Tombstone Interaction (RTBF and Legal Hold) {#section-24-3}

#### §24.3.1 Default Behavior (legal_hold: false) {#section-24-3-1}

When a tombstone is issued with `legal_hold: false` (the default):

<ol className="stigmem-steps">
<li>The tombstoned entity's facts MUST be excluded from ALL <code>as_of</code> queries, regardless of whether <code>as_of</code> predates the tombstone's <code>created_at</code>.</li>
<li>The tombstone has retroactive effect: the knowledge graph history is presented as if the entity never appeared.</li>
<li>This applies to <code>query_facts</code>, <code>recall</code>, and graph traversal results regardless of the <code>as_of</code> timestamp.</li>
</ol>

This is the normative RTBF semantic: the data subject's right to erasure extends to historical query results.

The 60-second LRU cache refresh window defined in §23.3.3 rule 4 applies equally to `as_of` queries. During this window, a recently tombstoned entity MAY appear in `as_of` results on nodes whose local cache has not yet refreshed.

#### §24.3.2 Legal-Hold Behavior (legal_hold: true) {#section-24-3-2}

When a tombstone is issued with `legal_hold: true`:

<ol className="stigmem-steps">
<li>Live recall queries MUST still exclude the entity's facts — suppressed from live recall identically to <code>legal_hold: false</code>.</li>
<li>Time-travel queries (<code>as_of</code> parameter) MAY return the entity's facts, but MUST annotate them with <code>"tombstone_status": "legal_hold"</code> in the response (§24.3.3).</li>
<li>Callers MUST be authenticated with an admin API key to receive <code>legal_hold</code>-annotated facts. Agent API keys MUST NOT receive them, even in an <code>as_of</code> context.</li>
<li>Intended for regulatory use cases where a data controller must preserve historical records for audit or legal proceedings while still suppressing the entity from operational recall.</li>
</ol>

<div className="stigmem-keypoint">

**Operators MUST NOT set `legal_hold: true` absent a documented legal basis.**

Issuing a `legal_hold` tombstone MUST emit an
`rtbf_legal_hold_issued` audit log event (§22.3).

</div>

#### §24.3.3 Legal-Hold Response Annotation {#section-24-3-3}

Facts returned under a `legal_hold` tombstone MUST include the following annotation in the response envelope:

```json
{
  "facts": [...],
  "tombstone_notices": [
    {
      "entity_uri":           "user:alice",
      "tombstone_id":         "tomb_01J...",
      "legal_hold":           true,
      "tombstone_created_at": "2026-05-01T10:00:00Z"
    }
  ]
}
```

The `tombstone_notices` array MUST be present in every `as_of` response that returns `legal_hold` facts. It MUST NOT be present when no `legal_hold` tombstones apply to the result set.

### §24.4 Storage-Trait Extension {#section-24-4}

The following methods MUST be added to the storage trait for time-travel support:

```
query_facts_as_of(
  entity_uri:      string | null,
  scope:           FactScope | null,
  relation:        string | null,
  as_of:           ISO8601,
  is_admin_caller: bool,           // controls legal_hold visibility (§24.3.2)
  limit:           int,
  cursor:          string | null
) → { facts: [FactRecord], cursor: string | null, tombstone_notices: [TombstoneNotice] }

recall_as_of(
  intent:          string,
  scope:           FactScope | null,
  as_of:           ISO8601,
  is_admin_caller: bool,
  max_chunks:      int,
  include_graph:   bool
) → { chunks: [RecallChunk], tombstone_notices: [TombstoneNotice] }
```

Implementations of `query_facts_as_of` MUST apply tombstone filtering per §24.3 before returning results. The `as_of` timestamp MUST be passed through to the storage layer as a query parameter and MUST NOT be applied as a post-filter on an unfiltered full scan.

<div className="stigmem-keypoint">

**The storage layer MUST NOT rely solely on the API layer to gate `legal_hold` facts.**

When `is_admin_caller` is `false`, facts covered by a `legal_hold`
tombstone MUST be excluded from results (identically to
`legal_hold: false` tombstones); when `true`, they MAY be returned
and MUST be annotated via `tombstone_notices`.

</div>

**Cursor stability:** `as_of` query cursors are NOT tombstone-stable snapshots. If a tombstone is applied between paginated requests, rows visible on page 1 may be absent from page 2. Callers MUST NOT infer tombstone suppression from inter-page result-count differences.

### §24.5 Wire Format {#section-24-5}

#### §24.5.1 As-Of Recall {#section-24-5-1}

Time-travel recall uses the same `POST /v1/recall` endpoint with an additional `as_of` parameter. The response shape is identical to a standard recall response but includes a `tombstone_notices` array that surfaces any RTBF tombstones (§23) affecting the result set. Legal-hold visibility is governed by the caller's API key type: agent keys receive silently filtered results to prevent information leakage, while admin keys receive explicit tombstone notices.

```
POST /v1/recall
Authorization: Bearer <agent or admin api-key>
Content-Type: application/json

{
  "intent":    "what did Alice prefer last year?",
  "as_of":     "2025-01-01T00:00:00Z",
  "scope":     "company",
  "max_facts": 20
}
→ 200 {
    "chunks":            [...RecallChunk...],
    "tombstone_notices": []
  }
→ 400 as_of_invalid_timestamp       if timestamp is malformed
→ 400 as_of_future                  if timestamp is in the future
→ 400 as_of_before_retention_floor  if timestamp predates retention horizon
→ 200 with empty `tombstone_notices` and facts silently filtered, if the query would surface legal_hold
        facts and the caller is an **agent** API key
→ 403 as_of_legal_hold_forbidden    if the query would return legal_hold facts and the caller is an **admin**
        API key but the deployment is configured to deny admin as_of access to that entity
```

<div className="stigmem-keypoint">

**Agent API key callers MUST NOT receive any response that reveals the existence or absence of a legal-hold tombstone.**

When an agent-key `as_of` query would surface `legal_hold` facts,
the node MUST return `200` with results silently filtered — identical
to non-legal-hold tombstone behavior. `tombstone_notices` is populated
only when `legal_hold` tombstones apply AND the caller is an admin
API key.

</div>

#### §24.5.2 As-Of Fact Query {#section-24-5-2}

The structured fact query endpoint also accepts `as_of` for time-travel. Unlike the recall endpoint, the fact query returns raw `FactRecord` objects rather than recall chunks, making it suitable for programmatic audits and compliance reporting. The same tombstone-filtering and legal-hold visibility rules from §24.5.1 apply.

```
GET /v1/facts?entity_uri=user:alice&as_of=2025-01-01T00:00:00Z&scope=company
Authorization: Bearer <admin api-key>

→ 200 {
    "facts":             [...FactRecord...],
    "tombstone_notices": [...]
  }
→ 400 as_of_invalid_timestamp
→ 400 as_of_future
→ 403 as_of_legal_hold_forbidden
```

### §24.6 Error Reference {#section-24-6}

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Error code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>as_of_invalid_timestamp</code></span></dt>
<dd><code>as_of</code> parameter is not a valid ISO 8601 timestamp.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>as_of_future</code></span></dt>
<dd><code>as_of</code> timestamp is in the future.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>as_of_before_retention_floor</code></span></dt>
<dd><code>as_of</code> predates the deployment's minimum retention horizon.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type"><code>as_of_legal_hold_forbidden</code></span></dt>
<dd>Query would surface legal-hold tombstoned facts and the caller is an admin API key but the deployment denies admin time-travel access to that entity; MUST NOT be returned to agent API key callers (use silent 200 filter instead).</dd>
</div>

</div>

---
