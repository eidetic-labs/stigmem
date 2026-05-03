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
)
page = client.query(entity="user:alice", scope="company")
```

## License

Apache-2.0
