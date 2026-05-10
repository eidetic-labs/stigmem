---
title: §24. Time-Travel / As-Of Queries
sidebar_label: §24 Time-Travel / As-Of Queries
audience: Spec
description: "Stigmem spec section 24 — as_of parameter on /v1/recall and /v1/facts; append-only retraction log."
---

# §24. Time-Travel / As-Of Queries {#section-24}

**Status:** DRAFT normative (v1.1-draft, Phase 13)

as_of parameter on /v1/recall and /v1/facts; append-only retraction log.

**Authoritative source:** [`spec/stigmem-spec-v1.1-draft.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.1-draft.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** DRAFT normative (Phase 13). §24.1–§24.6 carry MUST/SHOULD/MAY normative language.

### §24.1 Scope {#section-24-1}

Time-travel queries allow callers to retrieve the state of the knowledge graph at a past point in time. This enables historical auditing, debugging, regulatory compliance reporting, and causal provenance reconstruction.

The `as_of` parameter is an ISO 8601 timestamp specifying the point-in-time to query. An `as_of` query returns facts as they were visible to an ordinary query at that timestamp, subject to tombstone interaction rules (§24.3).

### §24.2 As-Of Query Semantics {#section-24-2}

#### §24.2.1 Fact Visibility at Time T {#section-24-2-1}

A fact `f` is **visible at time T** if all of the following conditions hold:

1. `f.created_at <= T` — the fact had been written before or at T.
2. `f.valid_until is null OR f.valid_until > T` — the fact had not yet expired at T.
3. `f.confidence > 0 at time T` — the fact had not been retracted by T. Retraction is governed by the `fact_retractions` append-only log (see §23.5.3 Migration 013c). A fact `f` is considered retracted at T if and only if a row exists in `fact_retractions` with `fact_id = f.id` and `retracted_at <= T`. The in-place `confidence = 0.0` on the `facts` row is used for live (non-`as_of`) queries only; `query_facts_as_of` MUST join `fact_retractions` on this condition and MUST NOT use the `facts.confidence` field as a proxy for retraction state at historical timestamps.
4. No active tombstone (§23.3) covers `f.entity` with a scope matching `f.scope`, unless the tombstone has `legal_hold: true` (§24.3). **Note:** because tombstone suppression is retroactive (§24.3.1), the fact-visibility definition at time T is not a purely historical snapshot — it reflects present tombstone state. Callers MUST NOT assume that a result set for `as_of=T` is immutable; a subsequently issued tombstone will retroactively change it. This means the monotonicity invariant (§24.2.3) holds only before accounting for tombstones, retraction, or expiry.

#### §24.2.2 Query Interface {#section-24-2-2}

The `as_of` parameter MUST be accepted on the following endpoints:

```
GET  /v1/recall?intent=<string>&as_of=<ISO8601>&...
POST /v1/recall   { "intent": "...", "as_of": "2025-01-01T00:00:00Z", ... }
GET  /v1/facts?entity_uri=<string>&as_of=<ISO8601>&...
```

The `as_of` timestamp MUST be validated as:
- A valid ISO 8601 timestamp.
- Not in the future (at most the server's current clock + 5 seconds tolerance for clock skew).
- Not older than the retention horizon configured for the deployment. Operators MAY configure a minimum `as_of` floor; queries before the floor MUST return `as_of_before_retention_floor`.

#### §24.2.3 Monotonicity Invariant {#section-24-2-3}

The `as_of` result set MUST be monotonically consistent: for any two queries with `as_of=T1 < T2`, the set of facts visible at T1 MUST be a subset of the facts visible at T2, before accounting for tombstones, retraction, or expiry. This invariant allows callers to reason about the causal evolution of the knowledge graph.

### §24.3 Tombstone Interaction (RTBF and Legal Hold) {#section-24-3}

#### §24.3.1 Default Behavior (legal_hold: false) {#section-24-3-1}

When a tombstone is issued with `legal_hold: false` (the default):

1. The tombstoned entity's facts MUST be excluded from ALL `as_of` queries, regardless of whether `as_of` predates the tombstone's `created_at`.
2. The tombstone has retroactive effect: the knowledge graph history is presented as if the entity never appeared.
3. This applies to `query_facts`, `recall`, and graph traversal results regardless of the `as_of` timestamp.

This is the normative RTBF semantic: the data subject's right to erasure extends to historical query results.

The 60-second LRU cache refresh window defined in §23.3.3 rule 4 applies equally to `as_of` queries. During this window, a recently tombstoned entity MAY appear in `as_of` results on nodes whose local cache has not yet refreshed. This window is bounded and does not affect the retroactive semantics of the tombstone once the cache refreshes.

#### §24.3.2 Legal-Hold Behavior (legal_hold: true) {#section-24-3-2}

When a tombstone is issued with `legal_hold: true`:

1. Live recall queries (`GET /v1/recall`, `recall_instruction`) MUST still exclude the entity's facts — the entity is suppressed from the live knowledge graph identically to `legal_hold: false`.
2. Time-travel queries (`as_of` parameter) MAY return the entity's facts, but MUST annotate them with `"tombstone_status": "legal_hold"` in the response (§24.3.3).
3. Callers of `as_of` queries MUST be authenticated with an admin API key to receive `legal_hold`-annotated facts. Agent API keys MUST NOT receive `legal_hold`-annotated facts, even in an `as_of` context.
4. The `legal_hold` flag is intended for regulatory use cases where a data controller must preserve historical records for audit or legal proceedings while still suppressing the entity from operational recall.

Operators MUST NOT set `legal_hold: true` absent a documented legal basis. Issuing a `legal_hold` tombstone MUST emit an `rtbf_legal_hold_issued` audit log event (§22.3).

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
  is_admin_caller: bool,           // controls legal_hold visibility (§24.3.2)
  max_chunks:      int,
  include_graph:   bool
) → { chunks: [RecallChunk], tombstone_notices: [TombstoneNotice] }
```

Implementations of `query_facts_as_of` MUST apply tombstone filtering per §24.3 before returning results. The `as_of` timestamp MUST be passed through to the storage layer as a query parameter and MUST NOT be applied as a post-filter on an unfiltered full scan.

The `is_admin_caller` parameter governs `legal_hold` fact visibility: when `false`, facts covered by a `legal_hold` tombstone MUST be excluded from results (identically to `legal_hold: false` tombstones); when `true`, they MAY be returned and MUST be annotated via `tombstone_notices`. The storage layer MUST NOT rely solely on the API layer to gate `legal_hold` facts.

**Cursor stability:** `as_of` query cursors are NOT tombstone-stable snapshots. If a tombstone is applied between paginated requests, rows visible on page 1 may be absent from page 2. Callers MUST NOT infer tombstone suppression from inter-page result-count differences. The spec does not require implementations to snapshot tombstone state per cursor; it does require that page 2 results are tombstone-filtered at the time of the page 2 request.

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
        facts and the caller is an **agent** API key (indistinguishable from a non-legal-hold empty result)
→ 403 as_of_legal_hold_forbidden    if the query would return legal_hold facts and the caller is an **admin**
        API key but the deployment is configured to deny admin as_of access to that entity
```

Agent API key callers MUST NOT receive any response that reveals the existence or absence of a legal-hold tombstone. When an agent-key `as_of` query would surface `legal_hold` facts, the node MUST return `200` with results silently filtered (as if the entity never had matching facts) — identical to non-legal-hold tombstone behavior.

`tombstone_notices` is populated only when `legal_hold` tombstones apply AND the caller is an admin API key.

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

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `as_of_invalid_timestamp` | `as_of` parameter is not a valid ISO 8601 timestamp |
| 400 | `as_of_future` | `as_of` timestamp is in the future |
| 400 | `as_of_before_retention_floor` | `as_of` predates the deployment's minimum retention horizon |
| 403 | `as_of_legal_hold_forbidden` | `as_of` query would surface legal-hold tombstoned facts and the caller is an admin API key but the deployment denies admin time-travel access to that entity; MUST NOT be returned to agent API key callers (use silent 200 filter instead) |

---
