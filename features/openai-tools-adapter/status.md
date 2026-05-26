# OpenAI Tools Adapter Status

The OpenAI tools adapter is active for the v0.9.0a10 adapter publication
batch. Source layout, package metadata, discovery manifest, feature records,
security review, and mocked tests are complete for v0.1.0 publication.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| Default surface | `opt-in` |
| Owner | `unowned` |
| Package | `stigmem-plugin-openai-tools-adapter` |
| Implementation | `experimental/openai-tools-adapter` |
| Publication state | `published` - v0.1.0 package metadata, discovery manifest, mocked tests, and feature records are complete for the v0.9.0a10 adapter batch. |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Source and documentation existed as experimental adapter surface area. | `experimental/openai-tools-adapter/README.md`; `experimental/openai-tools-adapter/STATUS.md` |
| `v0.9.0a10` | Packaged as `stigmem-plugin-openai-tools-adapter` v0.1.0 with plugin manifest and mocked validation. | `experimental/openai-tools-adapter/pyproject.toml`; `experimental/openai-tools-adapter/evidence.md` |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | Adapter implementation, package metadata, and mocked tests exist under `experimental/openai-tools-adapter`. |
| Feature record | Complete | ADR-020 feature record added under `features/openai-tools-adapter`. |
| Package validation | Complete | `stigmem-plugin-openai-tools-adapter` v0.1.0 metadata and build inputs are present. |
| Dependency validation | Complete for package scope | Provider dependencies are optional extras: `litellm`, `openai`, and `providers`. |
| Live provider validation | Operator-owned | Live LiteLLM, OpenAI SDK, and local Ollama checks remain deployment gates, not v0.1.0 package blockers. |
| Ownership | Open | Owner remains unassigned for live provider certification. |

## Current Gaps

- The adapter has mocked unit coverage but no current live model validation
  evidence.
- Ownership remains unresolved for live provider certification.
