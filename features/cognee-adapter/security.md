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
| Cognee transitive `diskcache` exposure | The published adapter package does not hard-depend on Cognee and no longer publishes a `cognee` extra while Cognee resolves `diskcache==5.6.3` (`CVE-2025-69872`). | `experimental/cognee-adapter/pyproject.toml`; `experimental/cognee-adapter/README.md` |
| Cognee outage or failure | The adapter is a secondary enrichment layer; Stigmem remains the source of exact facts and callers own retry/degradation policy. | `experimental/cognee-adapter/README.md` |
| Ambiguous result provenance | Normalized fallback records use `source=cognee` and `relation=cognee:result` for opaque results. | `experimental/cognee-adapter/adapter.py`; `experimental/cognee-adapter/tests/test_cognee_adapter.py` |

## Residual Risk

- Stigmem facts sent to Cognee may be processed by third-party LLM providers
  depending on Cognee configuration.
- Local vector database files may retain sensitive fact text after deletion
  from Stigmem.
- The adapter does not enforce redaction, retention, or dataset isolation.
- Live security validation remains design-partner/operator-owned for v0.1.0.
- Operators that install Cognee separately for live bridge use must accept and
  mitigate Cognee's current transitive `diskcache` cache-directory risk until
  Cognee or DiskCache publishes an audited non-vulnerable dependency path.

## Advisories and Findings

| Finding | Severity | Disposition |
| --- | --- | --- |
| Dependabot #52 / `CVE-2025-69872` — `diskcache<=5.6.3` unsafe pickle deserialization through Cognee | High upstream impact when an attacker can write to the cache directory | The Stigmem Cognee adapter removed its `cognee` optional dependency extra before v0.9.0a10 tagging. Default plugin installs and the Stigmem meta-package no longer resolve Cognee or DiskCache. Live Cognee deployments remain operator-owned until Cognee or DiskCache publishes an audited non-vulnerable dependency path. |
