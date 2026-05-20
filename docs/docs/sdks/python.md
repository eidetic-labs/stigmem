---
title: Python SDK Reference
sidebar_label: Python SDK
description: API reference for stigmem-py — StigmemClient, AsyncStigmemClient, models, and exceptions.
audience: Integrator
---

# Python SDK Reference

<p className="stigmem-meta"><span>5 min read</span><span>Python integrator</span><span>stigmem-py</span></p>

<div className="stigmem-lead">

**What this page covers**

`stigmem-py` is the official Python client for the Stigmem REST
API. It covers facts, conflicts, federation, recall, memory cards,
and subscriptions.

</div>

**Audience:** Python developers integrating with a Stigmem node.

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

```python
StigmemClient(url: str, api_key: str | None = None, timeout: float = 10.0)
```

<div className="stigmem-keypoint">

**Synchronous client. All methods raise `StigmemHTTPError` subclasses on non-2xx responses.**

Supports use as a context manager: `with StigmemClient(...) as client: ...`

</div>

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

Assert a retraction (`confidence=0.0`). Convenience wrapper around `assert_fact`.

#### `get` · `query`

```python
client.get(fact_id: str) -> Fact

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

`get` fetches a single fact by ID. `query` is a paginated structured query.

### Recall

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
    verify_full: bool = False,
) -> RecallResponse
```

Hybrid recall — return the most salient facts for `query` within `token_budget`. Combines lexical (FTS5/BM25), dense-vector (ANN), and graph-traversal signals.

<div className="stigmem-keypoint">

**Set `verify_full=True` to send `Stigmem-Verify: full`.**

Requests server-side integrity proof metadata, including the
current fact-chain proof when the node can provide it.

</div>

**`RecallResponse` fields:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>recall_id</code></dt>
<dt><span className="stigmem-fields__type">str</span></dt>
<dd>UUID for this recall call.</dd>
</div>

<div>
<dt><code>query_hash</code></dt>
<dt><span className="stigmem-fields__type">str</span></dt>
<dd>SHA-256 of the query string.</dd>
</div>

<div>
<dt><code>facts</code></dt>
<dt><span className="stigmem-fields__type">list[ScoredFact]</span></dt>
<dd>Ranked, token-budget-packed facts.</dd>
</div>

<div>
<dt><code>total_scored</code></dt>
<dt><span className="stigmem-fields__type">int</span></dt>
<dd>Candidates scored before packing.</dd>
</div>

<div>
<dt><code>token_budget</code> / <code>tokens_used</code></dt>
<dt><span className="stigmem-fields__type">int</span></dt>
<dd>Requested vs actual budget.</dd>
</div>

<div>
<dt><code>truncated</code></dt>
<dt><span className="stigmem-fields__type">bool</span></dt>
<dd>True when budget was exhausted.</dd>
</div>

<div>
<dt><code>chain_proof</code></dt>
<dt><span className="stigmem-fields__type">FactChainProof | None</span></dt>
<dd>Full-verification fact-chain metadata when requested.</dd>
</div>

</div>

`ScoredFact` fields include `fact`, `score`, `score_breakdown`, `hop_distance`, `token_estimate`, and `from_card`.

### Verification helpers

The SDK exposes local integrity helpers for clients that need to fail closed on tampered responses:

```python
from stigmem import (
    StigmemVerificationError,
    compute_fact_cid,
    verify_fact_chain_proof,
    verify_fact_cid,
)

result = client.recall("project status", verify_full=True)

try:
    for scored in result.facts:
        verify_fact_cid(scored.fact)
    verify_fact_chain_proof(result.chain_proof, require_checkpoint=True)
except StigmemVerificationError as exc:
    raise RuntimeError(f"Stigmem verification failed: {exc}") from exc
```

<div className="stigmem-keypoint">

**Rekor cryptographic inclusion verification remains a node/operator responsibility.**

It requires live log trust roots that the SDK does not embed.
`verify_fact_chain_proof` validates compact proof metadata and
deterministic local transparency-log checkpoint payloads only.

</div>

### Memory cards

```python
client.get_card(
    entity_uri: str,
    *,
    scope: FactScope = "local",
    refresh: bool = False,
) -> MemoryCard
```

Fetch the synthesized memory card for `entity_uri`. The card is auto-refreshed when stale. Pass `refresh=True` to force a server-side recomputation. Raises `StigmemNotFoundError` when the entity has no live facts.

```python
from stigmem import StigmemClient, MemoryCard
from stigmem.exceptions import StigmemNotFoundError

client = StigmemClient(url="http://localhost:8000", api_key="sk-...")

try:
    card: MemoryCard = client.get_card("stigmem://company.example/user/alice", scope="local")
    print(card.summary)
    print(f"confidence={card.avg_confidence:.3f}  stale={card.is_stale}")
    print(f"contradictions={card.has_contradictions}")
except StigmemNotFoundError:
    print("Entity has no live facts")

# Force refresh
card = client.get_card("stigmem://company.example/project/phase9", refresh=True)
```

**`MemoryCard` fields:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>entity_uri</code></dt>
<dt><span className="stigmem-fields__type">str</span></dt>
<dd>Entity the card describes.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">str</span></dt>
<dd>Scope the card was materialised from.</dd>
</div>

<div>
<dt><code>summary</code></dt>
<dt><span className="stigmem-fields__type">str</span></dt>
<dd>Structured text summary of live facts.</dd>
</div>

<div>
<dt><code>fact_hashes</code></dt>
<dt><span className="stigmem-fields__type">list[str]</span></dt>
<dd>SHA-256(fact_id) for each contributing fact.</dd>
</div>

<div>
<dt><code>avg_confidence</code></dt>
<dt><span className="stigmem-fields__type">float</span></dt>
<dd>Source-trust-weighted mean confidence.</dd>
</div>

<div>
<dt><code>refreshed_at</code></dt>
<dt><span className="stigmem-fields__type">str | None</span></dt>
<dd>ISO 8601 UTC timestamp of last refresh.</dd>
</div>

<div>
<dt><code>is_stale</code></dt>
<dt><span className="stigmem-fields__type">bool</span></dt>
<dd>True when a new fact has been asserted since the last refresh.</dd>
</div>

<div>
<dt><code>has_contradictions</code></dt>
<dt><span className="stigmem-fields__type">bool</span></dt>
<dd>True when any two live facts share the same relation.</dd>
</div>

</div>

### Conflicts · Federation · Node info

```python
client.list_conflicts(
    *,
    status: str | None = "unresolved",
    cursor: str | None = None,
    limit: int = 50,
) -> ConflictPage

client.resolve_conflict(
    conflict_id: str,
    *,
    winning_fact_id: str | None = None,
    resolution_note: str = "",
    new_value: FactValue | None = None,
) -> ConflictResolution

client.federation_status() -> list[Peer]
client.node_info() -> NodeInfo   # GET /.well-known/stigmem
```

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

## Exceptions

<div className="stigmem-fields">

<div>
<dt>Exception</dt>
<dt><span className="stigmem-fields__type">HTTP status</span></dt>
<dd>When raised</dd>
</div>

<div>
<dt><code>StigmemHTTPError</code></dt>
<dt><span className="stigmem-fields__type">any non-2xx</span></dt>
<dd>Base class.</dd>
</div>

<div>
<dt><code>StigmemAuthError</code></dt>
<dt><span className="stigmem-fields__type">401 / 403</span></dt>
<dd>Invalid or missing API key.</dd>
</div>

<div>
<dt><code>StigmemNotFoundError</code></dt>
<dt><span className="stigmem-fields__type">404</span></dt>
<dd>Resource does not exist.</dd>
</div>

<div>
<dt><code>StigmemConflictError</code></dt>
<dt><span className="stigmem-fields__type">409</span></dt>
<dd>Conflicting resource state.</dd>
</div>

</div>

```python
from stigmem.exceptions import StigmemNotFoundError, StigmemAuthError

try:
    card = client.get_card("stigmem://company.example/user/unknown")
except StigmemNotFoundError:
    print("Entity not found")
except StigmemAuthError:
    print("Check your API key")
```

## See also

<div className="stigmem-grid">

<div><h4><a href="../concepts/recall/">Recall guide</a></h4><p>Hybrid recall, weight tuning, fast-path.</p></div>
<div><h4><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/recall-graph">Memory Cards guide</a></h4><p>Card lifecycle and divergence policy.</p></div>
<div><h4><a href="../concepts/facts/asserting-facts">Asserting facts</a></h4><p>Detailed fact write patterns.</p></div>
<div><h4><a href="../concepts/facts/querying-facts">Querying facts</a></h4><p>Structured predicate queries.</p></div>

</div>
