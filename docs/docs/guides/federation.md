---
id: federation
title: Federation
sidebar_label: Federation
---

# Federation

**Audience:** Node operators connecting multiple Stigmem nodes.

:::info Coming soon
Full federation guide content is planned for the next docs sprint.
:::

## Overview

Federation lets two Stigmem nodes exchange facts within agreed scopes. The full protocol is defined in spec §6.

High-level flow:

1. Node A registers with Node B (`POST /v1/federation/peers`) with an Ed25519 declaration signature
2. Node B verifies the signature against Node A's `/.well-known/stigmem` public key
3. Node A's background pull loop periodically fetches new facts from Node B using a scoped peer token

## Quick start

```bash
# 1. Get Node B's well-known metadata (for its node_id and pubkey)
curl http://nodeB:8000/.well-known/stigmem | jq .

# 2. Register Node A with Node B
#    (declaration_sig generation requires the Ed25519 key — see spec §6.1)
curl -X POST http://nodeB:8000/v1/federation/peers \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <nodeB-key>' \
  -d '{
    "node_id": "stigmem:node:nodeA",
    "node_url": "http://nodeA:8000",
    "allowed_scopes": ["company", "public"],
    "declaration_sig": "<base64url-sig>"
  }'

# 3. List peers on Node B
curl http://nodeB:8000/v1/federation/peers \
  -H 'X-API-Key: <nodeB-key>' | jq .
```

## Conflict detection during ingest

When a node ingests a federated fact that conflicts with a locally-held fact (same entity/relation/scope, different value), it records a `ConflictRecord` and surfaces the contradiction to callers. Full semantics are in spec §6.5.

**Reserved-namespace exemption:** Facts whose entity or relation starts with the bare `stigmem:` prefix (e.g., `stigmem:conflict:status`, `stigmem:resolves`) are **exempt** from this detection. They carry protocol state, not semantic content, so two differing values represent a state transition rather than a conflict. Facts with a `stigmem://` URI entity (user content) are not covered by this exemption and remain subject to normal contradiction detection. See spec §5.10 and §6.5.

## Cursor-based resume after restart or partition {#soak-results}

The pull loop persists cursor positions in the `replication_cursors` table across both process restarts and network interruptions.

**Verified behavior (4-node soak, 2026-05-02 — [ACM-101](/ACM/issues/ACM-101)):**

- `TestCursorResume::test_node_restart_resumes_without_gaps` — 5 public facts asserted on a peer while the local node was stopped; on restart with the same SQLite DB, all 5 facts were recovered within 30s via cursor-resume pull. No manual intervention required.
- `TestPartialFailure::test_partial_ingest_then_resume` — 20-fact partial-crash scenario; correct cursor position and zero duplicates after resume.
- Idempotent ingest: re-delivered facts (same fact ID) are silently discarded — no duplicates even if the pull window overlaps the pre-crash window.

```bash
# Watch cursor behavior in node logs
stigmem node logs --follow | grep "pull from"

# Healthy cursor resume
INFO  pull from stigmem://node-b: cursor=1725349500000.005, got 12 facts, has_more=false

# Full re-pull after cursor loss
INFO  pull from stigmem://node-b: cursor=None, got 100 facts, has_more=true
```

If a node loses its `replication_cursors` table (DB loss/corruption), see the
[DB-loss recovery guide](./cursor-reset-recovery) for the `cursor-export` / `cursor-import`
procedure that bounds re-pull cost.

## Topics to be covered

- Generating Ed25519 keys and declaration signatures (spec §6.1)
- Peer token format and verification (spec §6.3)
- Scope enforcement and security invariants (spec §6.4)
- Monitoring the federation audit log
- Configuring `STIGMEM_FEDERATION_PULL_INTERVAL_S`

See the [Federation API Reference](/docs/api-reference) and the [Architecture overview](/docs/architecture) for internals.
