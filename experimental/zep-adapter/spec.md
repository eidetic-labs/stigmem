---
spec_id: Spec-X7-Zep-Adapter
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0a10 plugin package
last_updated: 2026-05-26
supersedes: features/zep-adapter/spec.md package projection
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
title: Zep Adapter
sidebar_label: Zep Adapter
audience: Spec
description: "Package projection for Zep adapter semantics."
stability: experimental
since: 0.9.0a10
---

# Zep Adapter Spec

## Scope

The Zep adapter connects Stigmem fact dictionaries to Zep session memory. It
does not define Zep behavior, Stigmem node API semantics, or a required runtime
dependency for default Stigmem installs.

This package covers:

- the `stigmem-plugin-zep-adapter` package under `experimental/zep-adapter`;
- plugin discovery through the `stigmem.plugins` entry-point group;
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
| `plugin_manifest()` | Returns the discovery manifest for `stigmem-plugin-zep-adapter` v0.1.0. |

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

- Making Zep required for Stigmem node availability.
- Deduplicating mirrored facts inside Zep.
- Defining new Stigmem protocol semantics.
- Owning live Zep Cloud or self-hosted Zep acceptance for every operator.

## Canonical Spec Assignment

The canonical feature spec assignment is `Spec-X7-Zep-Adapter`. The adapter is
an external integration spec around existing Stigmem fact/query behavior, not a
new core protocol module.
