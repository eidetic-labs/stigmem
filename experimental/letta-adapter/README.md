# stigmem-plugin-letta-adapter

Bridges [Stigmem](https://github.com/eidetic-labs/stigmem) with
[Letta](https://github.com/letta-ai/letta), the open-source memory and
persistence layer for LLM agents.

This package is experimental and opt-in. Installing it makes the
`letta-adapter` plugin discoverable through the `stigmem.plugins` entry-point
group; host applications still choose when to call the adapter.

## Federation model

| Layer | Scope | Memory style |
|---|---|---|
| Stigmem | Multi-agent, cross-session | Shared coordination facts (typed, auditable) |
| Letta | Per-agent, in-context | Persistent blocks (core, archival, recall) |

The adapter writes Stigmem facts into a Letta agent's archival memory as
`[stigmem]`-tagged passages and reads them back as Stigmem-compatible records.
Native Letta passages can be returned as `letta:archival_memory` fallback
records or filtered with `stigmem_only=True`.

## Design

- Facts are serialized as structured text with a `[stigmem]` prefix.
- `pull_from_letta()` parses the prefix back to fact fields.
- `batch_push_to_letta()` pushes multiple facts to the same target agent.
- `letta` is a lazy optional import; discovery and tests do not require it.

## Files

| File | Purpose |
|---|---|
| `src/stigmem_plugin_letta/adapter.py` | Bridge adapter - serialization, Letta archival memory push/pull |
| `src/stigmem_plugin_letta/manifest.py` | Stigmem plugin discovery manifest |
| `tests/conftest.py` | pytest path setup |
| `tests/test_letta_adapter.py` | Unit tests (Letta client mocked; no live deps required) |

## Installation

```bash
python -m pip install 'stigmem-plugin-letta-adapter>=0.1.0,<2.0.0'
```

Install Letta only in deployments that run the live bridge:

```bash
python -m pip install 'stigmem-plugin-letta-adapter[letta]>=0.1.0,<2.0.0'
```

### Requirements

- Python >= 3.11
- `stigmem-py`: `pip install stigmem-py` (or from workspace)
- `letta`: optional runtime extra for live Letta calls; unit tests and plugin
  discovery do not require it.
- A running Letta server for live use: `letta server` (default:
  `http://localhost:8283`)

### Environment variables

```bash
LETTA_URL=http://localhost:8283  # default
LETTA_TOKEN=your-token           # optional for local server
```

## Usage

### Push a fact into a Letta agent's memory

```python
from stigmem_plugin_letta import StigmemLettaAdapter

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

### Seed an agent at startup

```python
from stigmem import StigmemClient

client = StigmemClient(url="http://localhost:8765")
page = client.query(entity="project:loom", scope="company")

bridge.batch_push_to_letta(
    [f.model_dump() for f in page.facts],
    agent_id="your-letta-agent-uuid",
)
```

### Pull agent memory as Stigmem records

```python
records = bridge.pull_from_letta(
    agent_id="your-letta-agent-uuid",
    scope="company",
)

stigmem_records = bridge.pull_from_letta(
    agent_id="your-letta-agent-uuid",
    scope="company",
    stigmem_only=True,
)
```

## Enable

The adapter has no node-global behavior gate at v0.1.0. Enable it in the host
application by installing the package and importing
`stigmem_plugin_letta.StigmemLettaAdapter`.

```bash
python -m pip install 'stigmem-plugin-letta-adapter>=0.1.0,<2.0.0'
python -m pip install 'stigmem-plugin-letta-adapter[letta]>=0.1.0,<2.0.0'  # live Letta bridge
stigmem plugins list
```

## Disable

Remove the adapter from the host application path and restart the process that
loads plugins. If it was installed only for this integration, uninstall it:

```bash
python -m pip uninstall stigmem-plugin-letta-adapter
```

## Test

```bash
cd experimental/letta-adapter
python -m pytest tests/ -v
```

No live Stigmem node or Letta server required; the `letta` module is mocked in
the test suite.

## Uninstall

```bash
python -m pip uninstall stigmem-plugin-letta-adapter
```

## Invariants

- The adapter only appends to archival memory; it never modifies core memory
  blocks or deletes passages.
- Letta is a secondary enrichment layer. Failures in `push_to_letta` or
  `pull_from_letta` do not affect Stigmem availability.
- Callers own retry, circuit-breaker, and prompt/write policy.
