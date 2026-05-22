---
spec_id: Spec-X3-Time-Travel-Queries
version: 0.1.0-alpha.0
status: Experimental
applies_to: v0.9.0a4 alpha plugin-validation line
last_updated: 2026-05-22
supersedes: pre-reset section 24 time-travel/as-of query material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-X2-RTBF-Tombstones >= 0.1.0-alpha.0
---

# Spec-X3-Time-Travel-Queries

## Extraction Status

This feature spec owns time-travel query semantics for ADR-020. The
compatibility file at `experimental/time-travel/spec.md` links here while the
implementation package remains under `experimental/time-travel/`.

The feature is experimental and opt-in for `v0.9.0a4`. Default installs MUST
reject `as_of` requests unless `stigmem-plugin-time-travel` is registered and
the relevant operator gate is explicitly enabled.

## Scope

Time-travel queries allow callers to retrieve the state of the knowledge graph
at a past point in time. This enables historical auditing, debugging,
regulatory compliance reporting, and causal provenance reconstruction.

The `as_of` parameter is an ISO 8601 timestamp specifying the point-in-time to
query. An `as_of` query returns facts as they were visible to an ordinary query
at that timestamp, subject to tombstone interaction rules.

## As-Of Query Semantics

A fact is visible at time `T` if all of the following conditions hold:

1. `created_at <= T`.
2. `valid_until is null OR valid_until > T`.
3. the fact had not been retracted at or before `T`;
4. no active tombstone covers the fact's entity and scope, unless the tombstone
   uses the legal-hold path and the caller is authorized.

The result set is monotonically consistent for two queries with `as_of=T1` and
`as_of=T2` where `T1 < T2`, before accounting for tombstones, retraction, or
expiry. Tombstones deliberately break pure historical monotonicity because RTBF
suppression is retroactive.

## Query Interface

The feature defines `as_of` support for:

```text
GET  /v1/recall?intent=<string>&as_of=<ISO8601>&...
POST /v1/recall   { "intent": "...", "as_of": "2025-01-01T00:00:00Z", ... }
GET  /v1/facts?entity_uri=<string>&as_of=<ISO8601>&...
```

The timestamp MUST be:

- a valid ISO 8601 timestamp;
- not in the future, allowing bounded server clock tolerance;
- not older than the configured retention floor.

Default installs that receive `as_of` MUST fail closed with
`time_travel_plugin_not_loaded`. Registered plugins whose operator gates remain
disabled MUST fail closed with `time_travel_plugin_disabled`.

## Tombstone Interaction

When a tombstone is issued with `legal_hold: false`, the tombstoned entity's
facts MUST be excluded from all `as_of` queries, including queries whose
timestamp predates the tombstone.

When a tombstone is issued with `legal_hold: true`:

- live recall still suppresses the entity;
- admin-authorized `as_of` queries MAY return preserved facts;
- returned legal-hold facts MUST include `tombstone_notices`;
- agent API keys MUST NOT receive a response that reveals the existence or
  absence of legal-hold tombstones.

## Storage-Trait Extension

The feature requires historical fact and recall storage behavior equivalent to:

```text
query_facts_as_of(entity_uri, scope, relation, as_of, is_admin_caller, limit, cursor)
recall_as_of(intent, scope, as_of, is_admin_caller, max_chunks, include_graph)
```

Implementations MUST apply tombstone filtering before returning results and
MUST NOT rely solely on API-layer filtering for legal-hold boundaries.

## Wire Format

Time-travel recall uses the ordinary recall endpoint with an `as_of` parameter.
Responses have the same shape as standard recall responses and include
`tombstone_notices` when legal-hold facts are returned to authorized admin
callers.

Structured fact queries accept `as_of` for programmatic audit and compliance
reporting. They follow the same tombstone and legal-hold visibility rules.

## Error Conditions

| HTTP | Error code | Condition |
| --- | --- | --- |
| 400 | `as_of_invalid_timestamp` | `as_of` is not a valid ISO 8601 timestamp. |
| 400 | `as_of_future` | `as_of` is in the future. |
| 400 | `as_of_before_retention_floor` | `as_of` predates the deployment retention floor. |
| 403 | `time_travel_plugin_disabled` | Plugin is registered but the requested `as_of` surface is not enabled by operator configuration. |
| 403 | `as_of_legal_hold_forbidden` | Admin legal-hold historical access is denied by deployment policy. |
| 501 | `time_travel_plugin_not_loaded` | Default install received `as_of` without the plugin. |

## Non-Goals

- This feature does not graduate time-travel into the default supported surface.
- This feature does not publish a signed plugin artifact.
- This feature does not own tombstone policy except where historical reads must
  honor it.
