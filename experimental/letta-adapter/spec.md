---
spec_id: Spec-X7-Letta-Adapter
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0a10 plugin package
last_updated: 2026-05-26
supersedes: features/letta-adapter/spec.md package projection
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
title: Letta Adapter
sidebar_label: Letta Adapter
audience: Spec
description: "Package projection for Letta adapter semantics."
stability: experimental
since: 0.9.0a10
---

# Letta Adapter Spec

## Purpose

`stigmem-plugin-letta-adapter` bridges Stigmem's typed fact model with a Letta
agent's archival memory. It lets a host application append selected Stigmem
facts into a target agent and read tagged archival passages back as
Stigmem-compatible dictionaries.

The adapter is intentionally a bridge package, not a node-wide behavior plugin.
Installing it makes the `letta-adapter` manifest discoverable. Runtime calls
remain explicit through `StigmemLettaAdapter`.

## Passage Semantics

Stigmem facts are serialized into newline-separated text prefixed with
`[stigmem]`. The serialized fields include `entity`, `relation`, `value`,
`value_type`, `source`, `scope`, `confidence`, and `stigmem_id`.

Unprefixed Letta passages are returned as `relation="letta:archival_memory"`
fallback records unless callers pass `stigmem_only=True`.

## Configuration Surface

The adapter reads these environment variables through
`StigmemLettaAdapter.from_env()`:

| Variable | Purpose |
| --- | --- |
| `LETTA_URL` | Letta server URL, defaulting to `http://localhost:8283`. |
| `LETTA_TOKEN` | Optional Letta bearer token. |

## API

`StigmemLettaAdapter.from_env()` constructs an adapter from environment.

`push_to_letta(fact, agent_id=...)` serializes one fact and inserts it into the
target agent archival memory.

`batch_push_to_letta(facts, agent_id=...)` pushes multiple serialized facts to
the same target agent.

`pull_from_letta(agent_id, scope, stigmem_only=False, limit=50)` reads archival
memory and returns Stigmem-compatible dictionaries.

## Failure Modes

- Missing `letta` dependency raises `ImportError` with an install hint when a
  Letta operation is attempted.
- Letta server outages propagate to the caller; the adapter does not retry.
- Unprefixed passages are preserved as opaque text records unless filtered.
- Host applications must choose agent IDs, credentials, and write policy.
