# Cognee Adapter Security

## Threat Model Delta

The Cognee adapter can send Stigmem facts to an external knowledge-graph
runtime and an LLM-backed extraction pipeline. That makes dataset selection,
provider configuration, vector database location, API key handling, and
downstream retention part of the adapter security posture.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| External LLM exposure | Cognee LLM provider and API key are configured explicitly through environment variables; the adapter does not set a provider unless the relevant variables are present. | `experimental/cognee-adapter/adapter.py` |
| Local vector database persistence | The vector database provider and path are explicit configuration, defaulting to local LanceDB at `.cognee_db`. | `experimental/cognee-adapter/README.md`; `experimental/cognee-adapter/adapter.py` |
| Cognee outage or failure | The adapter is a secondary enrichment layer; Stigmem remains the source of exact facts and callers own retry/degradation policy. | `experimental/cognee-adapter/README.md` |
| Ambiguous result provenance | Normalized fallback records use `source=cognee` and `relation=cognee:result` for opaque results. | `experimental/cognee-adapter/adapter.py`; `experimental/cognee-adapter/tests/test_cognee_adapter.py` |

## Residual Risk

- Stigmem facts sent to Cognee may be processed by third-party LLM providers
  depending on Cognee configuration.
- Local vector database files may retain sensitive fact text after deletion
  from Stigmem.
- The adapter does not enforce redaction, retention, or dataset isolation.
- Live security validation remains design-partner/operator-owned for v0.1.0.

## Advisories and Findings

None currently recorded for the adapter.
