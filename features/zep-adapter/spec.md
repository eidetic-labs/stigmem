# Zep Adapter Spec

## Scope

The Zep adapter connects Stigmem facts to Zep session memory. It does not
define Zep behavior, Stigmem node API semantics, or a stable adapter packaging
contract.

This feature covers:

- the `stigmem-zep-adapter` source package under `experimental/zep-adapter`;
- formatting Stigmem fact dictionaries as `[STIGMEM]` structured Zep system
  messages;
- mirroring a fact into a target Zep session with `assert_to_zep`;
- reading Zep extracted episodic facts with `query_from_zep`;
- converting Zep facts into Stigmem-compatible dictionaries with
  `relation=zep:episodic_fact`;
- environment-based Zep Cloud API key, self-hosted base URL, and source entity
  configuration.

## Adapter Contract

| Surface | Behavior |
| --- | --- |
| `assert_to_zep(fact, session_id)` | Encodes one Stigmem fact as a structured system message and appends it to the target Zep session. |
| `query_from_zep(scope, session_id, limit)` | Fetches extracted facts from a Zep session and returns Stigmem-compatible dictionaries. |
| `fact_to_message_content(fact)` | Builds the `[STIGMEM] entity | relation: value (scope=..., confidence=...)` message body. |
| `zep_fact_to_stigmem_record(fact_text, session_id, scope, idx)` | Wraps a Zep extracted fact string as a Stigmem-shaped record. |

## Configuration

| Setting | Purpose |
| --- | --- |
| `ZEP_API_KEY` | Zep Cloud API key. |
| `ZEP_BASE_URL` | Base URL for self-hosted Zep. |
| `STIGMEM_SOURCE_ENTITY` | Source entity URI, defaulting to `agent:stigmem-zep`. |

## Session and Scope Behavior

Zep owns session boundaries. Stigmem owns fact scopes. The adapter stamps the
caller-supplied Stigmem scope onto returned records, but it does not filter
facts inside Zep by scope because Zep does not expose Stigmem scope semantics.

## Non-Goals

- Shipping the adapter in the current alpha artifact set.
- Defining stable Zep package compatibility.
- Deduplicating mirrored facts inside Zep.
- Making Zep required for Stigmem node availability.
- Defining new Stigmem protocol semantics.

## Canonical Spec Assignment

There is no Spec-X assignment for the Zep adapter. It is an external adapter
around existing Stigmem fact and query behavior, not a standalone Stigmem
protocol module.
