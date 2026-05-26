---
feature: zep-adapter
spec_id: Spec-X0-Zep-Adapter
status: Experimental
applies_to: stigmem v0.9.0a10
last_updated: 2026-05-26
owned_risks: []
contributed_risks:
  - R-01
  - R-02
  - R-21
---

# Zep Adapter Security Review

## Threat Model Delta

The Zep adapter can copy Stigmem facts into Zep session memory and read Zep
extracted episodic facts back as Stigmem-shaped records. That makes session
selection, provider/API-key configuration, scope stamping, extraction lag, and
downstream Zep retention part of the adapter security posture.

This adapter contributes to existing feature-security risks R-01, R-02, and
R-21 because host applications can route scoped fact content to an external
memory provider, then rehydrate provider-derived facts into Stigmem-shaped
records.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Wrong session target | All push and pull calls require an explicit `session_id`. | `src/stigmem_plugin_zep/adapter.py`; `tests/test_zep_adapter.py` |
| API key handling | The Zep Cloud API key is read from `ZEP_API_KEY`; no key value is committed to the source tree. | `README.md`; `src/stigmem_plugin_zep/adapter.py` |
| Scope confusion | Returned records are stamped with the caller-supplied Stigmem scope, and docs state that Zep itself does not filter by Stigmem scope. | `README.md`; `spec.md` |
| Zep outage or failure | Query failures return an empty result set and log a warning; callers own retry/degradation policy. | `src/stigmem_plugin_zep/adapter.py`; `tests/test_zep_adapter.py` |

## Residual Risk

- Stigmem facts copied into Zep may remain according to Zep retention behavior.
- Zep extracted facts may include sensitive user/session context.
- The adapter does not enforce redaction, retention, session authorization, or
  deduplication.
- Zep extraction is asynchronous, so recent facts may not be visible
  immediately after mirroring.
- Live Zep validation remains operator-owned for v0.1.0.

## Advisories and Findings

None currently recorded for the adapter.
