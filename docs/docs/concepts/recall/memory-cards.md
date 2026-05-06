---
title: Memory Cards
sidebar_label: Memory Cards
description: How Stigmem materialises per-entity summaries (memory cards) for fast recall queries — stale-on-write, refresh-on-read, and divergence policy (spec §20.4).
audience: Integrator
---

# Memory Cards

**Audience:** Node operators and agent developers who want to understand how Stigmem pre-aggregates entity knowledge for fast recall (spec §20.4).

A **memory card** is a per-entity, per-scope pre-computed summary materialised from an entity's live facts. Cards are stored in the `memory_cards` table and refreshed automatically when facts change. Fresh, high-confidence, contradiction-free cards short-circuit full raw-fact re-ranking in `recall`, reducing per-query work.

## Card schema

```sql
CREATE TABLE memory_cards (
    entity_uri         TEXT NOT NULL,
    tenant_id          TEXT NOT NULL,
    scope              TEXT NOT NULL,
    summary            TEXT NOT NULL,           -- structured text summary
    fact_hashes        TEXT NOT NULL,           -- JSON array of SHA-256 fact hashes
    avg_confidence     REAL NOT NULL DEFAULT 0.0,
    refreshed_at       TEXT,                    -- ISO 8601 UTC
    is_stale           INTEGER NOT NULL DEFAULT 0,
    has_contradictions INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entity_uri, tenant_id, scope)
);
```

The summary is structured text listing the entity and its top facts sorted by confidence:

```
Entity: stigmem://company.example/user/alice
Facts:
  memory:role: engineer (conf=1.00)
  memory:team: platform (conf=0.95)
  memory:timezone: UTC+1 (conf=0.90)
```

`avg_confidence` is a source-trust-weighted mean over the contributing facts (capped at 20 facts by default). Source-trust weights are clamped to a minimum of `0.01` so zero-trust sources still contribute mass.

## Card lifecycle

### 1. Stale-on-write

Every `POST /v1/facts` call triggers `mark_entity_stale` on the affected entity after the fact is persisted. This sets `is_stale = 1` on the card row (if one exists) via a non-blocking call using a short-lived DB connection. Errors are logged and suppressed — the write path is never blocked by card bookkeeping.

```
assert_fact(entity, relation, value, …)
  └─ persist fact to facts table
  └─ mark_entity_stale(entity_uri, scope, tenant_id)   ← non-blocking, errors suppressed
```

### 2. Refresh-on-read

`get_fresh_card` is called by both `GET /v1/cards/{entity_uri}` and the recall fast-path:

1. Look up the card row for `(entity_uri, tenant_id, scope)`.
2. If no row exists, or `is_stale = 1`, call `refresh_card`:
   - Query the top 20 live facts by `confidence DESC, timestamp DESC`, excluding retracted (`confidence = 0`) and quarantined facts.
   - Detect contradictions: flag `has_contradictions = 1` if any two facts share the same `relation`.
   - Compute source-trust-weighted `avg_confidence`.
   - Build the structured text summary.
   - Upsert the card row atomically (`INSERT … ON CONFLICT DO UPDATE`).
3. Return the fresh `MemoryCardData`.

### 3. Contradiction flag

During refresh, if any two facts for the entity share the same `relation`, `has_contradictions` is set to `1`. The card is still written and served — the flag signals to consumers that the summary may be partially unreliable and that the entity has unresolved conflicts worth reviewing via `GET /v1/conflicts`.

## Divergence policy

The recall fast-path in `POST /v1/recall` short-circuits raw-fact re-ranking for an entity **only when all three conditions hold:**

| Condition | Required value |
|-----------|----------------|
| `is_stale` | `false` |
| `has_contradictions` | `false` |
| `avg_confidence` | `≥ 0.5` (`CARD_MIN_CONFIDENCE`) |

If any condition is false — including a transient error in `get_fresh_card` — the entity falls through to full raw-fact re-ranking. The fallback is silent: no degraded-mode flag appears in the recall response, other than the absence of `from_card: true` on those facts.

Rationale: a card with contradictions or a stale confidence score is unsafe to use as a summary substitute. Falling through guarantees the caller always sees the most current ranked view.

## API: `GET /v1/cards/{entity_uri}`

Fetch (and optionally force-refresh) the memory card for a specific entity. Returns 404 when the entity has no live facts.

**Path parameter:**
- `entity_uri` — URL-encoded entity URI (e.g. `stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice`)

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | string | `"local"` | Scope the card was materialised from |
| `refresh` | boolean | `false` | Force a server-side refresh even if the card is already fresh |

**Auth:** read permission required.

**Example — fetch (refresh if stale):**

```bash
curl -s "http://localhost:8000/v1/cards/stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice?scope=local" \
  -H 'Authorization: Bearer <api-key>'
```

**Example — force refresh:**

```bash
curl -s "http://localhost:8000/v1/cards/stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice?scope=local&refresh=true" \
  -H 'Authorization: Bearer <api-key>'
```

**Response:**

```json
{
  "entity_uri": "stigmem://company.example/user/alice",
  "scope": "local",
  "summary": "Entity: stigmem://company.example/user/alice\nFacts:\n  memory:role: engineer (conf=1.00)\n  memory:team: platform (conf=0.95)",
  "fact_hashes": ["a1b2c3d4...", "e5f6a7b8..."],
  "avg_confidence": 0.975,
  "refreshed_at": "2026-05-04T11:30:00+00:00",
  "is_stale": false,
  "has_contradictions": false
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Invalid `scope` value or malformed `entity_uri` |
| 403 | API key lacks read permission |
| 404 | No live facts exist for the entity |

## Python SDK

```python
from stigmem import StigmemClient, MemoryCard
from stigmem.exceptions import StigmemNotFoundError

client = StigmemClient(url="http://localhost:8000", api_key="sk-...")

# Fetch card — refreshes automatically if stale
try:
    card: MemoryCard = client.get_card(
        "stigmem://company.example/user/alice",
        scope="local",
    )
    print(card.summary)
    print(f"confidence={card.avg_confidence:.3f}  contradictions={card.has_contradictions}")
except StigmemNotFoundError:
    print("No facts found for this entity")

# Force refresh regardless of staleness
card = client.get_card(
    "stigmem://company.example/project/phase9",
    scope="local",
    refresh=True,
)
```

Async:

```python
from stigmem import AsyncStigmemClient

async with AsyncStigmemClient(url="http://localhost:8000", api_key="sk-...") as client:
    card = await client.get_card("stigmem://company.example/user/alice")
    print(f"stale={card.is_stale}  refreshed={card.refreshed_at}")
```

## `MemoryCard` model

```python
from stigmem import MemoryCard  # re-exported from stigmem.models

class MemoryCard(BaseModel):
    entity_uri: str
    scope: str
    summary: str
    fact_hashes: list[str]    # SHA-256(fact_id) for each contributing fact
    avg_confidence: float     # source-trust-weighted mean
    refreshed_at: str | None  # ISO 8601 UTC
    is_stale: bool
    has_contradictions: bool
```

:::note Phase 9 — draft
Memory cards are part of spec §20, currently a draft. The API shape is stable for testing; it will be promoted to normative in Phase 14.
:::

## See also

- [Recall guide](./recall.md) — how the card fast-path integrates into hybrid recall
- [Architecture: memory cards](/docs/next/reference/architecture/index.md#memory-cards) — design rationale and garden ACL requirement (R2)
- [Python SDK reference](/docs/build/sdks/python) — full `StigmemClient` API
