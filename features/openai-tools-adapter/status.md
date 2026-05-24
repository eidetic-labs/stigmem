# OpenAI Tools Adapter Status

The OpenAI tools adapter is deferred for the current alpha artifact set. Source
and mocked tests exist, but release-line validation is not complete.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Owner | `unowned` |
| Package | `stigmem-openai-tools-adapter` |
| Implementation | `experimental/openai-tools-adapter` |
| Publication state | `defer` - live provider validation, package validation, dependency validation, and ownership remain unresolved. |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Source and documentation existed as experimental adapter surface area. | `experimental/openai-tools-adapter/README.md`; `experimental/openai-tools-adapter/STATUS.md` |
| `0.9.xA` planned | Keep the adapter discoverable while ownership, package, dependency, and live model validation remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | Adapter implementation, package metadata, and mocked tests exist under `experimental/openai-tools-adapter`. |
| Feature record | Complete | ADR-020 feature record added under `features/openai-tools-adapter`. |
| Package validation | Open | Package metadata has not been promoted into the current alpha artifact set. |
| Dependency validation | Open | Optional `litellm` and `openai` runtime paths need release-line dependency checks. |
| Live provider validation | Open | No recorded live LiteLLM, OpenAI SDK, or local Ollama validation for the current release line. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- The adapter has mocked unit coverage but no current live model validation
  evidence.
- Optional provider dependencies are not release-line pinned in the default
  alpha artifact set.
- Ownership and publication disposition remain unresolved.
