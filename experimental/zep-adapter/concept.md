---
title: Zep
sidebar_label: Zep
audience: Integrator
---

# Stigmem ↔ Zep

Federation bridge between Stigmem (shared multi-agent coordination memory) and
[Zep](https://www.getzep.com) (per-user/session episodic memory).

## Federation model

Stigmem and Zep address complementary memory scopes.  This adapter lets them
hydrate each other:

| Direction | What happens |
|---|---|
| **assert** (stigmem → Zep) | A stigmem fact is written as a `system` message into the Zep session.  Zep's extractor surfaces it in the session's episodic context. |
| **query** (Zep → stigmem) | Zep's extracted propositions for a session are returned as stigmem-compatible FactRecord dicts for re-assertion or query hydration. |

## Prerequisites

- Python ≥ 3.11
- `pip install zep-cloud`
- A running Stigmem node and a Zep instance (or Zep Cloud API key)

## Install

Install the adapter package:

```bash
python -m pip install 'stigmem-plugin-zep-adapter[zep]>=0.1.0,<2.0.0'
```

## Environment variables

```bash
# Zep (use one)
ZEP_API_KEY=your-zep-cloud-key        # Zep Cloud
ZEP_BASE_URL=http://localhost:8000    # self-hosted Zep

# stigmem
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key           # optional
STIGMEM_SOURCE_ENTITY=agent:stigmem-zep
```

## Usage

### Mirror a stigmem fact into Zep

```python
from stigmem_plugin_zep import StigmemZepAdapter

adapter = StigmemZepAdapter.from_env()

# fact_dict is any stigmem FactRecord dict
result = adapter.assert_to_zep(fact_dict, session_id="session-abc")
# → {"session_id": "session-abc", "content": "[STIGMEM] ...", "ok": True}
```

### Hydrate from Zep episodic memory

```python
records = adapter.query_from_zep("company", session_id="session-abc")
for r in records:
    print(r["entity"], r["relation"], r["value"]["v"])
```

### Run the demo

```bash
cd stigmem
STIGMEM_URL=http://localhost:8765 \
ZEP_BASE_URL=http://localhost:8000 \
SESSION_ID=demo-001 \
uv run python experimental/zep-adapter/demo.py
```

The demo asserts a fact via the stigmem REST API, mirrors it to Zep, and
reads back the session's episodic facts.

## Running tests

```bash
cd stigmem
uv run pytest experimental/zep-adapter/tests/ -v
```

No live Zep instance required — Zep client calls are mocked with
`unittest.mock`.

## Protocol notes

- **Extraction lag**: Zep extracts facts from messages asynchronously.  A newly
  written message may not appear in `query_from_zep` immediately; allow a few
  seconds between `assert_to_zep` and `query_from_zep`.
- **Idempotency**: `assert_to_zep` does not deduplicate — asserting the same fact
  twice writes two messages.  Track mirrored fact IDs at the call site if needed.
- **Scope semantics**: `query_from_zep` stamps the supplied `scope` onto returned
  records, but Zep has no scope concept — all facts for the session are returned.

## See also

- [Gemini connector](./gemini) — Gemini native function-calling format
- [Authentication](../../security/authentication) — Stigmem API key setup
