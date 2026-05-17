# stigmem-py

Python client SDK for [Stigmem](https://github.com/eidetic-labs/stigmem) — the federated knowledge fabric.

## Install

```bash
pip install stigmem-py
```

## Quick start

```python
from stigmem import StigmemClient, string_value

client = StigmemClient(url="http://localhost:8765", api_key="sk-...")
fact = client.assert_fact(
    entity="user:alice",
    relation="memory:role",
    value=string_value("CEO"),
    source="agent:cto",
    session_id="session:example",
)
page = client.query(entity="user:alice", scope="company")
```

## Session and provenance options

Agent integrations should pass a stable `session_id` on reads and writes so the
node can enforce same-session read/write graph isolation. Writes that summarize
facts read earlier in the same session should use
`write_mode="summarize_with_provenance"` and carry source facts in
`derived_from`.

```python
from stigmem import text_value

client.assert_fact(
    entity="handoff:session-123",
    relation="intent:handoff_summary",
    value=text_value("Summarized context for the next agent."),
    source="agent:openclaw",
    session_id="session:example",
    write_mode="summarize_with_provenance",
    derived_from=[{"fact_id": "fact-source-001"}],
)
```

## License

Apache-2.0
