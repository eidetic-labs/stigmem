---
title: Python SDK Reference
sidebar_label: Python SDK
description: API reference for stigmem-py — StigmemClient, AsyncStigmemClient, models, and exceptions.
audience: Integrator
---

# Python SDK Reference

**Audience:** Python developers integrating with a Stigmem node.

`stigmem-py` is the official Python client for the Stigmem REST API. It covers facts, conflicts, federation, recall, memory cards, and subscriptions.

## Installation

```bash
pip install stigmem-py
# or with uv:
uv add stigmem-py
```

## Quick start

```python
from stigmem import StigmemClient
from stigmem.models import string_value

client = StigmemClient(url="http://localhost:8000", api_key="sk-...")

# Assert a fact
fact = client.assert_fact(
    entity="stigmem://company.example/user/alice",
    relation="memory:role",
    value=string_value("engineer"),
    source="agent:assistant",
)

# Recall relevant context
result = client.recall("what is Alice's current role?", token_budget=1000)
for sf in result.facts:
    print(f"[{sf.score:.3f}] {sf.fact.relation}: {sf.fact.value.v}")

# Fetch entity summary card
card = client.get_card("stigmem://company.example/user/alice")
print(card.summary)
```

## `StigmemClient`

Synchronous client. All methods raise `StigmemHTTPError` subclasses on non-2xx responses.

```python
StigmemClient(url: str, api_key: str | None = None, timeout: float = 10.0)
```

Supports use as a context manager (`with StigmemClient(...) as client: ...`).

### Facts

#### `assert_fact`

```python
client.assert_fact(
    entity: str,
    relation: str,
    value: FactValue,
    source: str,
    *,
    confidence: float = 1.0,
    scope: FactScope = "company",
    valid_until: str | None = None,
) -> Fact
```

Assert a new fact. Returns the stored `Fact`. Raises `StigmemConflictError` (409) if a contradicting fact exists and the node is in strict conflict mode.

#### `retract`

```python
client.retract(
    entity: str,
    relation: str,
    scope: FactScope,
    source: str,
    *,
    value: FactValue | None = None,
) -> Fact
```

Assert a retraction (confidence=0.0). Convenience wrapper around `assert_fact`.

#### `get`

```python
client.get(fact_id: str) -> Fact
```

Fetch a single fact by ID. Raises `StigmemNotFoundError` (404) when absent.

#### `query`

```python
client.query(
    *,
    entity: str | None = None,
    relation: str | None = None,
    source: str | None = None,
    scope: FactScope | None = None,
    min_confidence: float | None = None,
    include_contradicted: bool = False,
    include_expired: bool = False,
    cursor: str | None = None,
    limit: int = 50,
    after: str | None = None,
) -> FactPage
```

Paginated fact query. Use `cursor` from the response to fetch the next page.

### Recall (v1.0 graph & recall — §20.3)

#### `recall`

```python
client.recall(
    query: str,
    *,
    scope: FactScope = "local",
    token_budget: int = 4000,
    depth: int = 2,
    weights: RecallWeights | None = None,
    min_confidence: float = 0.1,
    include_neighbors: bool = True,
    limit: int = 100,
) -> RecallResponse
```

Hybrid recall — return the most salient facts for `query` within `token_budget`. Combines lexical (FTS5/BM25), dense-vector (ANN), and graph-traversal signals. See the [Recall guide](../concepts/recall/) for details.

`RecallResponse` fields:

| Field | Type | Description |
|-------|------|-------------|
| `recall_id` | `str` | UUID for this recall call |
| `query_hash` | `str` | SHA-256 of the query string |
| `facts` | `list[ScoredFact]` | Ranked, token-budget-packed facts |
| `total_scored` | `int` | Candidates scored before packing |
| `token_budget` | `int` | Requested budget |
| `tokens_used` | `int` | Tokens actually used |
| `truncated` | `bool` | True when budget was exhausted |

`ScoredFact` fields include `fact`, `score`, `score_breakdown`, `hop_distance`, `token_estimate`, and `from_card` (see below).

### Memory cards (v1.0 graph & recall — §20.4)

#### `get_card`

```python
client.get_card(
    entity_uri: str,
    *,
    scope: FactScope = "local",
    refresh: bool = False,
) -> MemoryCard
```

Fetch the synthesized memory card for `entity_uri`. The card is auto-refreshed when stale. Pass `refresh=True` to force a server-side recomputation regardless of staleness.

Raises `StigmemNotFoundError` when the entity has no live facts.

```python
from stigmem import StigmemClient, MemoryCard
from stigmem.exceptions import StigmemNotFoundError

client = StigmemClient(url="http://localhost:8000", api_key="sk-...")

try:
    card: MemoryCard = client.get_card(
        "stigmem://company.example/user/alice",
        scope="local",
    )
    print(card.summary)
    print(f"confidence={card.avg_confidence:.3f}  stale={card.is_stale}")
    print(f"contradictions={card.has_contradictions}")
except StigmemNotFoundError:
    print("Entity has no live facts")

# Force refresh
card = client.get_card(
    "stigmem://company.example/project/phase9",
    refresh=True,
)
```

`MemoryCard` fields:

| Field | Type | Description |
|-------|------|-------------|
| `entity_uri` | `str` | Entity the card describes |
| `scope` | `str` | Scope the card was materialised from |
| `summary` | `str` | Structured text summary of live facts |
| `fact_hashes` | `list[str]` | SHA-256(fact_id) for each contributing fact |
| `avg_confidence` | `float` | Source-trust-weighted mean confidence |
| `refreshed_at` | `str \| None` | ISO 8601 UTC timestamp of last refresh |
| `is_stale` | `bool` | True when a new fact has been asserted since the last refresh |
| `has_contradictions` | `bool` | True when any two live facts share the same relation |

`from_card` on `ScoredFact`: when `True`, the fact is a synthetic card-summary produced by the recall fast-path rather than a raw stored fact.

### Conflicts

#### `list_conflicts`

```python
client.list_conflicts(
    *,
    status: str | None = "unresolved",
    cursor: str | None = None,
    limit: int = 50,
) -> ConflictPage
```

#### `resolve_conflict`

```python
client.resolve_conflict(
    conflict_id: str,
    *,
    winning_fact_id: str | None = None,
    resolution_note: str = "",
    new_value: FactValue | None = None,
) -> ConflictResolution
```

### Federation

#### `federation_status`

```python
client.federation_status() -> list[Peer]
```

Returns registered peers.

### Node info

#### `node_info`

```python
client.node_info() -> NodeInfo
```

Fetches `/.well-known/stigmem`.

---

## `AsyncStigmemClient`

Async version backed by `httpx.AsyncClient`. Supports `async with AsyncStigmemClient(...) as client:`.

All sync methods have async equivalents with the same signature — prefix with `await`:

```python
from stigmem import AsyncStigmemClient
from stigmem.models import string_value

async with AsyncStigmemClient(url="http://localhost:8000", api_key="sk-...") as client:
    fact = await client.assert_fact(
        entity="stigmem://company.example/user/alice",
        relation="memory:role",
        value=string_value("engineer"),
        source="agent:assistant",
    )
    card = await client.get_card("stigmem://company.example/user/alice")
    result = await client.recall("what is Alice's role?", token_budget=500)
```

---

## Value constructors

```python
from stigmem.models import (
    string_value,    # string_value("hello")
    text_value,      # text_value("long text...")
    number_value,    # number_value(3.14)
    boolean_value,   # boolean_value(True)
    datetime_value,  # datetime_value("2026-05-04T00:00:00Z")
    ref_value,       # ref_value("stigmem://...")
    null_value,      # null_value()
)
```

---

## Exceptions

| Exception | HTTP status | When raised |
|-----------|-------------|-------------|
| `StigmemHTTPError` | any non-2xx | Base class |
| `StigmemAuthError` | 401 / 403 | Invalid or missing API key |
| `StigmemNotFoundError` | 404 | Resource does not exist |
| `StigmemConflictError` | 409 | Conflicting resource state |

```python
from stigmem.exceptions import StigmemNotFoundError, StigmemAuthError

try:
    card = client.get_card("stigmem://company.example/user/unknown")
except StigmemNotFoundError:
    print("Entity not found")
except StigmemAuthError:
    print("Check your API key")
```

---

## See also

- [Recall guide](../concepts/recall/) — hybrid recall, weight tuning, fast-path
- [Memory Cards guide](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/recall-graph) — card lifecycle and divergence policy
- [Asserting facts](../concepts/facts/asserting-facts) — detailed fact write patterns
- [Querying facts](../concepts/facts/querying-facts) — structured predicate queries
