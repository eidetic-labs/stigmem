# Letta Adapter Spec

## Scope

The Letta adapter connects Stigmem facts to Letta agent archival memory. It
does not define Letta behavior, Stigmem node API semantics, or a stable adapter
packaging contract.

This feature covers:

- the `stigmem-plugin-letta-adapter` source package under
  `experimental/letta-adapter`;
- serialization of Stigmem fact dictionaries into `[stigmem]`-tagged archival
  memory passages;
- single-fact and batch insertion into a target Letta agent;
- archival-memory reads with Stigmem-prefixed passages parsed back into
  Stigmem-shaped records;
- optional inclusion or filtering of native Letta archival passages;
- environment-based Letta server URL and token configuration.

## Adapter Contract

| Surface | Behavior |
| --- | --- |
| `push_to_letta(fact, agent_id)` | Serializes one fact and inserts it into the target agent archival memory. |
| `batch_push_to_letta(facts, agent_id)` | Pushes multiple serialized facts to the same target agent. |
| `pull_from_letta(agent_id, scope, stigmem_only, limit)` | Reads archival memory and returns Stigmem-compatible dictionaries. |
| Non-Stigmem passages | Return as `relation=letta:archival_memory` unless `stigmem_only=True`. |

## Configuration

| Setting | Purpose |
| --- | --- |
| `LETTA_URL` | Letta server base URL, defaulting to `http://localhost:8283`. |
| `LETTA_TOKEN` | Optional bearer token for the Letta server. |

## Prefix Contract

The adapter uses `[stigmem]` as the archival-passage prefix for passages it
writes. Pull behavior depends on that prefix:

- prefixed passages are parsed into Stigmem-compatible fields;
- unprefixed passages become opaque `letta:archival_memory` records by
  default;
- `stigmem_only=True` excludes unprefixed passages.

## Non-Goals

- Defining stable Letta package compatibility beyond the v0.1.0 optional
  runtime extra.
- Modifying Letta core memory blocks or deleting Letta passages.
- Making Letta required for Stigmem node availability.
- Defining new Stigmem protocol semantics.

## Canonical Spec Assignment

`Spec-X7-Letta-Adapter` is the package projection for this external adapter.
It remains an adapter around existing Stigmem fact and query behavior, not a
standalone Stigmem protocol module.
