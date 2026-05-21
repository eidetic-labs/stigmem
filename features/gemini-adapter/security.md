# Gemini Adapter Security

## Threat Model Delta

The Gemini adapter can let a Gemini model call Stigmem read/write tools through
function-calling. That makes tool declaration accuracy, dispatch validation,
API key handling, source attribution, and bounded model loops part of the
adapter security posture.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Unbounded tool loop | The optional `run()` loop caps tool-call rounds. | `experimental/gemini-adapter/README.md`; `experimental/gemini-adapter/adapter.py` |
| Dispatch failure leakage | Dispatch errors are returned as JSON error payloads instead of crashing the loop. | `experimental/gemini-adapter/README.md`; `experimental/gemini-adapter/tests/test_gemini_adapter.py` |
| API key handling | Stigmem and Gemini keys are read from environment variables; no key values are committed to the source tree. | `experimental/gemini-adapter/README.md`; `experimental/gemini-adapter/adapter.py` |
| Source attribution | Assertions use an explicit source entity, defaulting to `agent:gemini`. | `experimental/gemini-adapter/README.md`; `experimental/gemini-adapter/adapter.py` |

## Residual Risk

- A Gemini model with tool access can attempt reads or writes allowed by the
  configured Stigmem credentials.
- The adapter does not define separate policy for model-requested writes.
- Live security validation is incomplete because the feature is deferred.

## Advisories and Findings

None currently recorded for the adapter.
