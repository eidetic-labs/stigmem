# stigmem-plugin-zep-adapter

Federation bridge between [Stigmem](https://github.com/eidetic-labs/stigmem)
and [Zep](https://www.getzep.com) session memory infrastructure.

This package is experimental and opt-in. Installing it makes the `zep-adapter`
plugin discoverable through the `stigmem.plugins` entry-point group; host
applications still choose when to call the adapter.

## Federation model

Stigmem and Zep address different memory scopes:

|  | Stigmem | Zep |
|---|---|---|
| Scope | Shared, multi-agent coordination | Per-user/per-session episodic |
| Granularity | Typed facts (`entity + relation + value`) | Conversational messages extracted into propositions |
| Consistency | Conflict detection and HLC ordering | Recency-weighted extraction |
| Audience | Agent network | Single LLM application |

The adapter mirrors Stigmem facts into Zep as structured `[STIGMEM]` system
messages and maps Zep extracted facts back into Stigmem-shaped records for
query hydration or re-assertion.

## Design

- `assert_to_zep()` writes a single Stigmem fact to a target Zep session.
- `query_from_zep()` reads Zep extracted facts and stamps the caller-supplied
  Stigmem scope onto returned records.
- Zep has no Stigmem scope model; callers own session authorization and
  downstream filtering.
- `zep-cloud` is a lazy optional import; discovery and tests do not require it.

## Files

| File | Purpose |
|---|---|
| `src/stigmem_plugin_zep/adapter.py` | Bridge adapter - encoding helpers, Zep session write, query, and record conversion |
| `src/stigmem_plugin_zep/manifest.py` | Stigmem plugin discovery manifest |
| `demo.py` | Optional live demo: assert a fact, mirror to Zep, verify extraction |
| `tests/conftest.py` | pytest path setup |
| `tests/test_zep_adapter.py` | Unit tests (Zep client mocked; no live deps required) |

## Installation

```bash
python -m pip install 'stigmem-plugin-zep-adapter>=0.1.0,<2.0.0'
```

Install Zep only in deployments that run the live bridge:

```bash
python -m pip install 'stigmem-plugin-zep-adapter[zep]>=0.1.0,<2.0.0'
```

Install demo dependencies only when running `demo.py`:

```bash
python -m pip install 'stigmem-plugin-zep-adapter[demo,zep]>=0.1.0,<2.0.0'
```

### Requirements

- Python >= 3.11
- `stigmem-py`: `pip install stigmem-py` (or from workspace)
- `zep-cloud`: optional runtime extra for live Zep calls; unit tests and plugin
  discovery do not require it.
- Zep Cloud API key or a self-hosted Zep base URL for live use.

### Environment variables

```bash
ZEP_API_KEY=your-zep-cloud-key        # Zep Cloud
ZEP_BASE_URL=http://localhost:8000    # self-hosted Zep
STIGMEM_SOURCE_ENTITY=agent:stigmem-zep
```

`demo.py` also reads:

```bash
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key
SESSION_ID=my-session-001
```

## Usage

### Mirror a Stigmem fact into Zep

```python
from stigmem_plugin_zep import StigmemZepAdapter

adapter = StigmemZepAdapter.from_env()

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
```

### Hydrate from Zep episodic memory

```python
records = adapter.query_from_zep("company", session_id="session-abc")
for record in records:
    print(record["value"]["v"])
```

### Run the demo

```bash
STIGMEM_URL=http://localhost:8765 \
ZEP_BASE_URL=http://localhost:8000 \
SESSION_ID=demo-001 \
python experimental/zep-adapter/demo.py
```

## Enable

The adapter has no node-global behavior gate at v0.1.0. Enable it in the host
application by installing the package and importing
`stigmem_plugin_zep.StigmemZepAdapter`.

```bash
python -m pip install 'stigmem-plugin-zep-adapter>=0.1.0,<2.0.0'
python -m pip install 'stigmem-plugin-zep-adapter[zep]>=0.1.0,<2.0.0'  # live Zep bridge
stigmem plugins list
```

## Disable

Remove the adapter from the host application path and restart the process that
loads plugins. If it was installed only for this integration, uninstall it:

```bash
python -m pip uninstall stigmem-plugin-zep-adapter
```

## Test

```bash
cd experimental/zep-adapter
python -m pytest tests/ -v
```

No live Zep instance or Stigmem node required; the Zep client is injected as a
`unittest.mock.MagicMock` via the `_zep_client` constructor parameter.

## Uninstall

```bash
python -m pip uninstall stigmem-plugin-zep-adapter
```

## Invariants

- The adapter appends to Zep session memory; it does not delete or deduplicate
  Zep messages.
- Zep extraction is asynchronous, so recently mirrored facts may not appear in
  `query_from_zep()` immediately.
- Zep is a secondary enrichment layer. Zep failures do not affect Stigmem node
  availability.
- Callers own retry, circuit-breaker, session authorization, redaction, and
  prompt/write policy.
