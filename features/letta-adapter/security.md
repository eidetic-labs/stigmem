# Letta Adapter Security

## Threat Model Delta

The Letta adapter can copy Stigmem facts into a Letta agent's archival memory
and read native Letta memories back as Stigmem-shaped records. That makes
agent selection, bearer-token handling, prefix hygiene, and downstream Letta
retention part of the adapter security posture.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Wrong agent target | All push and pull calls require an explicit `agent_id`. | `experimental/letta-adapter/src/stigmem_plugin_letta/adapter.py`; `experimental/letta-adapter/tests/test_letta_adapter.py` |
| Token handling | The Letta bearer token is read from `LETTA_TOKEN`; no token value is committed to the source tree. | `experimental/letta-adapter/README.md`; `experimental/letta-adapter/src/stigmem_plugin_letta/adapter.py` |
| Native memory confusion | The adapter prefixes Stigmem-origin passages and can filter reads to `stigmem_only=True`. | `experimental/letta-adapter/src/stigmem_plugin_letta/adapter.py`; `experimental/letta-adapter/tests/test_letta_adapter.py` |
| Letta outage or failure | The adapter is a secondary enrichment layer; Stigmem remains the source of exact facts and callers own retry/degradation policy. | `experimental/letta-adapter/README.md` |

## Residual Risk

- Stigmem facts copied into Letta archival memory may remain there according
  to Letta retention behavior.
- Native Letta archival passages returned as opaque records may include
  sensitive or agent-private content if callers do not use `stigmem_only=True`.
- The adapter does not enforce redaction, retention, or per-agent authorization.
- Live provider security validation remains design-partner/operator-owned for
  v0.1.0.

## Advisories and Findings

None currently recorded for the adapter.
