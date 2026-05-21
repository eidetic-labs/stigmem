# Zep Adapter Security

## Threat Model Delta

The Zep adapter can copy Stigmem facts into Zep session memory and read Zep
extracted episodic facts back as Stigmem-shaped records. That makes session
selection, provider/API-key configuration, scope stamping, extraction lag, and
downstream Zep retention part of the adapter security posture.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Wrong session target | All push and pull calls require an explicit `session_id`. | `experimental/zep-adapter/adapter.py`; `experimental/zep-adapter/tests/test_zep_adapter.py` |
| API key handling | The Zep Cloud API key is read from `ZEP_API_KEY`; no key value is committed to the source tree. | `experimental/zep-adapter/README.md`; `experimental/zep-adapter/adapter.py` |
| Scope confusion | Returned records are stamped with the caller-supplied Stigmem scope, and docs state that Zep itself does not filter by Stigmem scope. | `experimental/zep-adapter/README.md`; `features/zep-adapter/spec.md` |
| Zep outage or failure | Query failures return an empty result set and log a warning; callers own retry/degradation policy. | `experimental/zep-adapter/adapter.py`; `experimental/zep-adapter/tests/test_zep_adapter.py` |

## Residual Risk

- Stigmem facts copied into Zep may remain according to Zep retention behavior.
- Zep extracted facts may include sensitive user/session context.
- The adapter does not enforce redaction, retention, session authorization, or
  deduplication.
- Zep extraction is asynchronous, so recent facts may not be visible
  immediately after mirroring.
- Live security validation is incomplete because the feature is deferred.

## Advisories and Findings

None currently recorded for the adapter.
