# Stigmem — Letta Adapter

Bridges [stigmem](https://github.com/acme/stigmem) with
[Letta](https://github.com/letta-ai/letta) — the open-source memory and
persistence layer for LLM agents.

## Federation model

| Layer | Scope | Memory style |
|---|---|---|
| stigmem | Multi-agent, cross-session | Shared coordination facts (typed, auditable) |
| Letta | Per-agent, in-context | Persistent blocks (core, archival, recall) |

The two layers complement each other:

- **stigmem → Letta**: when a fact is asserted in stigmem (by any agent), push
  it into the target Letta agent's archival memory so the agent sees it in its
  next turn without reloading from stigmem at runtime.
- **Letta → stigmem**: read a Letta agent's archival memory and surface it as
  stigmem-compatible records so cross-agent queries can include per-agent context.

## Design

The adapter is intentionally thin:

- Facts are serialised as structured text with a `stigmem-fact:` prefix so they
  can be distinguished from other archival passages the agent may hold.
- `pull_from_letta()` parses the prefix back to fact fields.  Non-stigmem
  passages fall back to `relation: letta:archival_memory` with the raw text as
  value.
- `batch_push_to_letta()` reuses a single client for multiple inserts — preferred
  for seeding an agent's context at startup.
- `letta` is a lazy import; the module loads without it and raises `ImportError`
  with an install hint when the bridge methods are called.

## Files

| File | Purpose |
|---|---|
| `adapter.py` | Bridge adapter — serialisation, Letta archival memory push/pull |
| `tests/conftest.py` | pytest path setup |
| `tests/test_adapter.py` | Unit tests (letta client mocked; no live deps required) |

## Setup

### Requirements

- Python ≥ 3.11
- `stigmem-py`: `pip install stigmem-py` (or from workspace)
- `letta`: `pip install letta`
- A running Letta server: `letta server` (default: `http://localhost:8283`)

### Environment variables

```bash
# Letta server
LETTA_URL=http://localhost:8283  # default
LETTA_TOKEN=your-token           # optional for local server
```

## Usage

### Push a fact into a Letta agent's memory

```python
from adapter import StigmemLettaAdapter

bridge = StigmemLettaAdapter.from_env()

fact = {
    "entity": "project:loom",
    "relation": "roadmap:phase",
    "value": {"type": "string", "v": "phase-6"},
    "source": "agent:distsyseng",
    "scope": "company",
    "confidence": 1.0,
}

bridge.push_to_letta(fact, agent_id="your-letta-agent-uuid")
```

### Seed an agent at startup (batch)

```python
# Fetch relevant stigmem facts
from stigmem import StigmemClient
client = StigmemClient(url="http://localhost:8765")
page = client.query(entity="project:loom", scope="company")

# Push all into the agent's archival memory
bridge.batch_push_to_letta(
    [f.model_dump() for f in page.facts],
    agent_id="your-letta-agent-uuid",
)
```

### Pull agent memory as stigmem records

```python
records = bridge.pull_from_letta(
    agent_id="your-letta-agent-uuid",
    scope="company",
)

# Filter to only facts that were written by this adapter
stigmem_records = bridge.pull_from_letta(
    agent_id="your-letta-agent-uuid",
    scope="company",
    stigmem_only=True,
)
```

## Running tests

```bash
cd stigmem
uv run pytest adapters/letta/tests/ -v
```

No live stigmem node or Letta server required — the `letta` package is fully
mocked in the test suite.

## Invariants

- **Non-destructive**: the adapter only appends to archival memory; it never
  modifies core memory blocks or deletes passages.
- **Idempotency**: re-pushing the same fact text is safe — Letta deduplicates at
  the vector-store level.  However, identical text pushed twice may appear as
  duplicate passages in `list()` output.
- **Blast radius**: Letta is a secondary enrichment layer.  Failures in
  `push_to_letta` or `pull_from_letta` do not affect stigmem availability.
  Callers own the retry/circuit-breaker policy.
- **Prefix hygiene**: passages without the `stigmem-fact:` prefix are treated as
  opaque Letta memories; `stigmem_only=True` excludes them from pull results.
