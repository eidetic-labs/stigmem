---
spec_id: Spec-X2-RTBF-Tombstones
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-21
supersedes: pre-reset section 23 right-to-be-forgotten tombstone material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-05-Federation-Trust >= 0.1.0-alpha.0
  - Spec-09-Audit-Log >= 0.1.0-alpha.0
---

# Spec-X2-RTBF-Tombstones

## Scope

RTBF tombstones define signed records that suppress facts about a target entity
from recall, query, graph traversal, subscriptions, and federation propagation.
Tombstones are protocol primitives for erasure workflows; they are not legal
determinations.

## Tombstone Record Shape

A tombstone record identifies the target entity, scope pattern, issuing admin,
signature material, creation time, and legal-hold mode. Records are immutable.
Reinstatement requires a separate tombstone revocation record.

Key invariants:

- tombstone IDs use the `tomb_` prefix;
- entity URIs are exact, not wildcarded;
- issuance requires an admin authority;
- signatures cover the canonical body, excluding `signature` and `reason`;
- `reason` may be redacted for federation rebroadcast.

## Recall-Time Filtering

Before returning facts or memory cards, the node must resolve active tombstones
for candidate entities and suppress covered facts, graph references, memory
cards, and provenance entries. Suppression must not leak pre-filter counts or
aggregates.

Tombstone visibility must be consistent within the query execution scope.
SQLite implementations use immediate tombstone reads; PostgreSQL
implementations use at least read-committed visibility for tombstone reads
issued after the query plan is complete.

## Federation Propagation

Tombstones and revocations propagate through dedicated federation surfaces.
Peers verify the issuing identity and signature, write records idempotently, and
apply the recall-time filter. Failed verification must emit audit evidence.

## Legal Hold

`legal_hold: true` suppresses live reads while preserving historical access for
authorized admin/legal-hold flows. Non-admin callers must not be able to infer
legal-hold presence from `as_of` behavior.

## Non-Goals

- This feature does not graduate tombstones into the default install.
- This feature does not provide legal advice or determine whether erasure is
  required.
- This feature does not publish a signed plugin artifact yet.
