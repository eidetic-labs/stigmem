# Ollama/LiteLLM Adapter Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `superseded` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |

The legacy Ollama/LiteLLM concept remains useful as a connector identity, but
the implementation is the OpenAI-compatible tools adapter. This record
therefore points at `experimental/openai-tools-adapter` rather than describing
a separate implementation.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Ollama/LiteLLM connector documentation existed as experimental adapter surface area. | `experimental/ollama-litellm-adapter/STATUS.md`; `experimental/ollama-litellm-adapter/concept.md` |
| `0.9.xA` planned | Keep Ollama/LiteLLM as compatibility terminology while consolidating implementation detail under the OpenAI-compatible tools adapter. | `experimental/openai-tools-adapter/`; `docs/internal/feature-tracker.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Legacy identity preservation | Keep the Ollama/LiteLLM connector discoverable. | Complete | This feature record. |
| Implementation consolidation | Point behavior and test evidence at the OpenAI-compatible tools adapter. | Complete | `experimental/openai-tools-adapter/` |
| Live model validation | Validate supported Ollama/LiteLLM model behavior. | Open | None currently recorded. |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- This feature has no separate implementation tree.
- Live Ollama and LiteLLM model validation evidence is not complete.
- Package and version compatibility evidence remain deferred to the
  OpenAI-compatible tools adapter.
