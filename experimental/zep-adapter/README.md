# Stigmem — Zep Adapter

Federation bridge between [Stigmem](../../README.md) and [Zep](https://www.getzep.com)
memory infrastructure.

## Federation model

Stigmem and Zep address different memory scopes:

|  | Stigmem | Zep |
|---|---|---|
| **Scope** | Shared, multi-agent coordination | Per-user / per-session episodic |
| **Granularity** | Typed, namespaced facts (`entity + relation + value`) | Conversational messages → extracted propositions |
| **Consistency** | Conflict detection + HLC ordering | Recency-weighted extraction |
| **Audience** | Agent network | Single LLM application |

The seam this adapter implements:

- **assert direction** (`assert_to_zep`): when stigmem asserts a fact in a shared scope,
  mirror it as a Zep memory message for the relevant session/user.  Zep's extractor surfaces
  it alongside the session's episodic context.
- **query direction** (`query_from_zep`): when an agent queries a scope, optionally hydrate
  from Zep episodic memory — useful for per-user personalisation on top of the shared fact base.

## Files

| File | Purpose |
|---|---|
| `adapter.py` | Adapter — encoding helpers + `StigmemZepAdapter` class |
| `demo.py` | Runnable demo: assert a fact via stigmem, mirror to Zep, verify |
| `tests/conftest.py` | pytest path setup |
| `tests/test_adapter.py` | Unit tests (mock Zep client; no live Zep required) |

## Setup

### Requirements

- Python ≥ 3.11
- `zep-cloud`: `pip install zep-cloud`
- For the demo: a running stigmem node + a Zep instance or Zep Cloud API key

### Environment variables

```bash
# Zep (use one)
ZEP_API_KEY=your-zep-cloud-key        # Zep Cloud
ZEP_BASE_URL=http://localhost:8000    # self-hosted Zep

# stigmem (for demo.py and query_from_stigmem integration)
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key           # optional

# shared
STIGMEM_SOURCE_ENTITY=agent:stigmem-zep  # source URI on produced records
SESSION_ID=my-session-001                # for demo; auto-generated if unset
```

## Usage

### Mirror a stigmem fact into Zep

```python
from adapter import StigmemZepAdapter

adapter = StigmemZepAdapter.from_env()

# fact_dict is any stigmem FactRecord (plain dict)
fact_dict = {
    "id": "fact-123",
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "principal-engineer"},
    "source": "agent:my-agent",
    "scope": "company",
    "confidence": 1.0,
}
result = adapter.assert_to_zep(fact_dict, session_id="session-abc")
print(result["content"])
# → "[STIGMEM] user:alice | memory:role: principal-engineer (scope=company, confidence=1.00)"
```

### Hydrate from Zep episodic memory

```python
records = adapter.query_from_zep("company", session_id="session-abc")
for r in records:
    print(r["value"]["v"])
    # → each Zep-extracted episodic fact as a stigmem FactRecord dict
```

### Run the demo

```bash
cd stigmem
STIGMEM_URL=http://localhost:8765 \
ZEP_BASE_URL=http://localhost:8000 \
SESSION_ID=demo-001 \
uv run python adapters/zep/demo.py
```

## Running tests

```bash
cd stigmem
uv run pytest adapters/zep/tests/ -v
```

No live Zep instance or stigmem node required — the Zep client is injected as a
`unittest.mock.MagicMock` via the `_zep_client` constructor parameter.

## Protocol notes

- **Message role**: facts are written as `"system"` role messages.  Zep attributes system
  messages as ground truth, not user-authored ephemera, so the fact survives summarisation
  cycles longer than user-role messages would.
- **Extraction lag**: Zep's fact extractor runs asynchronously.  A freshly written message
  may not appear in `memory.get(session_id).facts` immediately; allow a few seconds and
  re-run `query_from_zep`.
- **Idempotency**: `assert_to_zep` does not deduplicate — asserting the same fact twice
  results in two messages.  If deduplication matters, track mirrored fact IDs at the call
  site.
- **Zep SDK**: targets `zep-cloud` (works for both Zep Cloud and self-hosted Zep ≥ 0.27).
  For the older `zep-python` SDK, instantiate `ZepClient` yourself and pass it via
  `_zep_client=` to use the dependency-injection path.
- **Scope semantics**: the `scope` parameter in `query_from_zep` is stamped onto returned
  records but not filtered on the Zep side — Zep has no concept of stigmem scopes.  All
  facts in a session are returned; the caller filters by scope if needed.

## See also

- [Letta adapter](../letta/README.md) — per-agent archival memory bridge
- [stigmem node README](../../node/README.md) — running a local node
- [Authentication](../../docs/docs/guides/authentication.md) — API key setup
