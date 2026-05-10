---
title: Design Partner Notes — the v0.8 design-partner window Pilots
sidebar_label: Design Partner Notes
audience: Integrator
---

# Design Partner Notes — the v0.8 design-partner window Pilots

**Audience:** Contributors and integrators evaluating stigmem for production adoption.

Three design-partner pilots ran during the v0.8 design-partner window: Zep, Letta, and Cognee. Each pilot produced a working adapter and surfaced feedback that shaped the v0.8 protocol decisions.

## Zep

**Adapter:** [`experimental/zep-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/zep-adapter) (deferred per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md))

Zep stores agent memory as session-scoped "propositions" extracted from dialogue. The adapter bridges these into stigmem facts and back.

**Key integration pattern:**
- `assert_to_zep(fact, session_id)` — encodes a stigmem `FactRecord` as a structured system message and appends it to a Zep session
- `query_from_zep(scope, session_id)` — fetches Zep's extracted propositions and converts them to `FactRecord`-compatible dicts

**Feedback themes:**
- Zep's proposition model is single-value-per-entity; stigmem's append-only facts give it more history. Adapters need a reconciliation step when pushing stigmem → Zep to avoid flooding Zep's memory with redundant propositions.
- The `scope` concept was well-received: Zep users wanted `session`-scoped facts to stay local. Using `scope=local` maps naturally — local facts never replicate.
- Confidence thresholds: Zep extracts propositions at varying confidence. The adapter passes Zep's confidence scores through as stigmem `confidence` values; downstream synthesis (`synthesize_scope`) correctly surfaces the lower-confidence alternatives.

**See also:** Zep connector guide (MCP host wiring) — coming in the connectors section

## Letta

**Adapter:** [`experimental/letta-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/letta-adapter) (deferred per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md))

Letta is an agent framework with first-class persistent memory blocks. The adapter federates stigmem facts into Letta's in-context memory and back.

**Key integration pattern:**
- Stigmem is used as the shared multi-agent coordination layer; Letta's memory blocks hold the per-agent working copy.
- On agent wake, `synthesize_scope` produces a clean conflict-resolved snapshot that is injected into Letta's memory block via the Letta Python SDK.
- On agent sleep, fact assertions in Letta's memory block are round-tripped back to stigmem.

**Feedback themes:**
- The `synthesize_scope` API was the primary integration point — Letta users needed exactly what synthesis provides: a single best-current-value per entity/relation without manual conflict resolution.
- Decay policies were useful for memory block hygiene: Letta agent memory tends to accumulate stale "task status" facts. The `memory:last_seen` retract policy cleaned these automatically.
- Contradiction detection fired frequently for task-status facts when two agents held different views. The Letta pilot drove the `alt_value` / `alt_confidence` fields in the `SynthesisEntry` response — callers needed to see the losing value, not just know a contradiction existed.

**See also:** [Synthesis guide](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/synthesis), [Decay guide](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/decay)

## Cognee

**Adapter:** [`experimental/cognee-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/cognee-adapter) (deferred per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md))

Cognee builds knowledge graphs from unstructured text. The adapter bridges stigmem's (entity, relation, value) triple model with Cognee's graph representation.

**Key integration pattern:**
- Cognee-extracted relationships are expressed as stigmem facts with `relation` URIs from the namespace registry (§9).
- The adapter maps Cognee graph edges → stigmem `(entity, relation, entity-ref)` triples.
- Scope is set based on the source document's confidentiality level.

**Feedback themes:**
- Namespace discipline mattered most here: Cognee extracts arbitrary relation labels; without normalization against the stigmem namespace registry (§9), facts from different Cognee runs used inconsistent relation URIs for the same semantic concept. The adapter now includes a relation normalization step.
- The `source` field (provenance) was well-received for audit purposes: Cognee users needed to know which document a fact came from. The adapter populates `source=cognee:doc:<hash>`.
- Fuzzy entity resolution  was flagged as important: Cognee often extracts the same entity with slightly different text forms (`"alice"` vs `"Alice Smith"`). The fuzzy entity resolver was accelerated by this feedback.

**See also:** Fuzzy entity resolver guide ; [Namespace registry spec §9](../spec/)

## Cross-pilot patterns

These themes emerged across all three pilots:

| Theme | Impact on v0.8 |
|-------|----------------|
| **Synthesis at boot** is the primary query pattern | `POST /v1/synthesis` and `synthesize_scope` MCP tool (§16) |
| **Contradiction visibility** — callers need the losing value, not just a flag | `alt_value` / `alt_confidence` in `SynthesisEntry` |
| **Decay for memory hygiene** — stale facts accumulate without eviction | `DecayPolicy` and `POST /v1/decay/sweep` (§15) |
| **Scope as authorization, not label** — local/company scoping needs to be strict | §6.8 scope propagation invariants |
| **Namespace discipline** — inconsistent relation URIs degrade query quality | Namespace registry §9; fuzzy entity resolver |

## Connector guides

For production wiring instructions, see the per-connector guides in the Connectors section (coming soon).
