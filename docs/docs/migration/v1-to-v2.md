---
title: Migrating from v1.x to v2.0
sidebar_label: v1.x → v2.0
description: "Step-by-step upgrade guide for Stigmem v1.x to v2.0 — federation trust, recall, lazy instructions, security hardening, RTBF, time-travel, CIDs."
audience: Operator
---

# Migrating from v1.x to v2.0

:::warning Retracted — neither v1.x nor v2.0 shipped publicly

Per [ADR-001](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/001-versioning.md), the canonical version line of stigmem begins at `v0.9.0a1` (2026-05-09). The version *markers* `v1.x` and `v2.0` referenced in this document labeled internal development checkpoints, not tagged public releases — there is no installed v1.x or v2.0 to migrate from. This document is preserved as historical record of an announced-but-withdrawn migration path.

If you have a stale dependency pinned to a `v1.x` or `v2.0` version that doesn't actually resolve (e.g., `stigmem-py>=1.0.0rc1` per the yanked `stigmem-openclaw` 1.0.3/1.0.5), see the [v0.9.0a1 release notes in CHANGELOG.md](https://github.com/Eidetic-Labs/stigmem/blob/main/CHANGELOG.md) for the canonical install path.

:::

**Audience:** Operators and developers running a stigmem node on v1.0 or pre-reset draft who want to upgrade to v2.0.

**Spec reference:** v2.0 promotes §19–§25 from draft to normative. §1–§18 are unchanged.

:::caution Breaking changes
v2.0 introduces new database migrations, mandatory mTLS for federation, and new wire-format fields. Read the full guide before upgrading a production node.
:::

---

## Upgrade overview

| Area | What changed | Spec section |
|------|-------------|--------------|
| Federation trust | Org manifests, capability tokens, transparency log | §19 |
| Recall & graph | Graph index, vector embeddings, hybrid recall, memory cards, subscriptions | §20 |
| Lazy instructions | Boot stub, instruction manifest, `recall_instruction` tool | §21 |
| Security hardening | mTLS, key rotation, audit log, quotas, replay protection | §22 |
| RTBF tombstones | Tombstone records, recall-time filter, federation propagation | §23 |
| Time-travel queries | `as_of` parameter on recall and facts endpoints | §24 |
| Content-addressed IDs | SHA-256 CIDs, dual addressing, federation tamper detection | §25 |

---

## Suggested cutover order

1. **Security hardening (§22)** — enable mTLS and audit logging first; all subsequent features depend on it.
2. **Federation trust (§19)** �� publish your org manifest and set up transparency log integration.
3. **Recall & graph (§20)** �� run the embedding backfill; enable the recall pipeline.
4. **Lazy instruction discovery (§21)** — migrate instruction files if applicable.
5. **RTBF tombstones (§23)** — enable the tombstone API and federation route.
6. **Time-travel queries (§24)** — available immediately after §23 migrations.
7. **Content-addressed IDs (§25)** — run `stigmem backfill-cids` last (non-blocking).

---

## What changed, what's experimental, what to watch

### Experimental features (not production-ready for all workloads)

Four v2.0 features are marked **EXPERIMENTAL** and carry warnings in their spec pages. They are shipped but are not yet recommended for all production use cases:

| Feature | Section | Primary risk | Constraint |
|---------|---------|-------------|------------|
| Lazy Instruction Discovery | §21 | Prompt injection via mutable manifest | Do not use for agents handling sensitive data or irreversible tool use until GA |
| RTBF Tombstones | §23 | Federated erasure may silently fail across nodes | Do not rely on tombstone federation for GDPR/CCPA compliance in multi-node deployments |
| Time-Travel Queries | §24 | `as_of` + tombstones can return post-erased data | Test isolation behavior on your production backend before compliance use |
| Content-Addressed Fact IDs | §25 | CID-less facts accepted from upgraded peers | Do not rely on CID as a security control in untrusted federation topologies |

See the [Experimental Features reference page](../reference/experimental-features.md) for the full canonical list and GA criteria.

### Operator warnings (GA features with non-obvious risks)

| Feature | Risk | Required action |
|---------|------|-----------------|
| §22.1 mTLS | Silent plaintext fallback behind reverse proxies | Set `STIGMEM_MTLS_REQUIRED=true` in production |
| §19.4 Source-trust cache | Per-worker incoherence in multi-worker deployments | Set `STIGMEM_TRUST_CACHE_BACKEND=redis` for production multi-worker |
| §6.7–§6.8 N-node backpressure/scope propagation | Draft spec; relay topologies not yet conformance-tested | Test your topology in staging |
| §19.5 Quarantine Garden | `trust_mode=strict` without quarantine garden permanently drops low-trust facts | Pre-create quarantine garden before enabling strict mode |

---

## Database migrations

v2.0 ships three new migrations that MUST be applied in order:

| Migration | Creates | Purpose |
|-----------|---------|---------|
| `013a` | `tombstones`, `tombstone_revocations` | RTBF tombstone storage (§23.5.3) |
| `013b` | `facts.cid` column, `fact_cid_aliases` | Content-addressed IDs (§25.3.1) |
| `013c` | `fact_retractions` | Append-only retraction log for time-travel (§24.2.1) |

Earlier phases (8–12) added migrations 006–012. If your node is on v1.0, you already have through 012. The node applies pending migrations on startup.

```bash
# Docker Compose (recommended)
git pull
docker compose up --build -d

# Verify migrations
curl -s http://localhost:8787/v1/admin/status | jq '.migrations'
```

### Rollback notes

Migrations 013a–013c are additive (new tables and columns). Rolling back requires:

1. Drop the `fact_retractions` table.
2. Drop the `fact_cid_aliases` table and `facts.cid` column.
3. Drop the `tombstones` and `tombstone_revocations` tables.

:::warning
Rolling back after tombstones have been issued will lose RTBF compliance state. Take a backup before upgrading.
:::

---

## Federation trust (§19)

### Breaking changes

| Change | Impact | Action required |
|--------|--------|-----------------|
| Org manifest required for federation | Peers reject connections without a valid manifest | Publish manifest at `/.well-known/stigmem-manifest.json` |
| Capability tokens replace ad-hoc trust | Existing peer connections will fail without tokens | Issue `federate` verb tokens for each peer |
| Transparency log integration | `trust_mode: strict` requires inclusion proofs | Configure Rekor or self-hosted log |
| 90-day token expiry ceiling | Tokens cannot exceed 90 days | Set up automated token renewal |

### Migration steps

1. **Generate an Ed25519 keypair** for your node:

```bash
stigmem keygen --out /etc/stigmem/node-key.pem
```

2. **Publish your org manifest:**

```bash
stigmem manifest publish \
  --entity-uri "stigmem://your-org/node-1" \
  --key /etc/stigmem/node-key.pem
```

3. **Issue capability tokens** for each federation peer:

```python
import httpx

resp = httpx.post("http://localhost:8787/v1/federation/tokens", json={
    "subject": "stigmem://peer-org/node-1",
    "verb": "federate",
    "object": "*",
})
token = resp.json()["token"]
```

4. **Configure trust mode:**

```bash
# Strict (requires transparency log — recommended for production)
export STIGMEM_FEDERATION_TRUST_MODE=strict

# Relaxed (accepts manifests without log proof — development only)
export STIGMEM_FEDERATION_TRUST_MODE=relaxed
```

### Rollback

Revert to v1.x federation by removing the `STIGMEM_FEDERATION_TRUST_MODE` env var. Peers on v2.0 will not connect until they also downgrade.

---

## Recall & graph (§20)

### Breaking changes

| Change | Impact | Action required |
|--------|--------|-----------------|
| `entity_edges` table materialized on startup | First boot after upgrade rebuilds the graph index | Allow extra startup time |
| Embedding storage (`vec_facts`) | Facts are embedded with `nomic-embed-text-v1.5` by default | Ensure Ollama is running or configure an alternative provider |
| `GET /v1/recall` replaces ad-hoc query patterns | Clients should adopt the recall endpoint | Update SDK calls |
| Graph depth capped at 3 | Requests with `depth > 3` return HTTP 400 | Update any client code using deeper traversal |

### Migration steps

1. **Ensure an embedding provider is available:**

```bash
# Default: Ollama with nomic-embed-text (local, Apache-2.0)
ollama pull nomic-embed-text

# Or use a cloud provider
export STIGMEM_EMBED_PROVIDER=openai
export STIGMEM_EMBED_MODEL=text-embedding-3-small
```

2. **Allow time for initial embedding backfill.** On first startup, the node embeds all existing facts. For large stores (100k+ facts), this may take several minutes.

3. **Adopt the recall API** in your agent code:

```python
resp = httpx.post("http://localhost:8787/v1/recall", json={
    "intent": "what does the user prefer?",
    "scope": "company",
    "max_facts": 20,
})
chunks = resp.json()["chunks"]
```

### New environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_EMBED_PROVIDER` | `ollama` | Embedding backend (`ollama`, `openai`, `voyage`) |
| `STIGMEM_EMBED_MODEL` | `nomic-embed-text` | Model name |
| `STIGMEM_EMBED_DIMENSIONS` | `768` | Vector dimensions (changing requires re-index) |
| `STIGMEM_CARD_MAX_AGE_S` | `86400` | Memory card invalidation age |
| `STIGMEM_SUBSCRIPTION_REPLAY_S` | `3600` | Subscription event replay window |

### Rollback

The `entity_edges` and `vec_facts` tables can be dropped without data loss — they are materialized views rebuilt on next startup.

---

## Lazy instruction discovery (§21)

### Breaking changes

| Change | Impact | Action required |
|--------|--------|-----------------|
| Boot stub replaces full instruction loading | Agents receive a ≤500-token preamble instead of full instructions | Author a boot stub and instruction manifest |
| `instruction:` scope reserved | Facts in this scope are governed by manifest rules | Rename any existing `instruction:*` facts if not using this feature |
| `recall_instruction` tool contract | Agents call this tool to load instructions on demand | Wire into your agent runtime |

### Migration steps

If you are **not** using lazy instructions, no action is required — the feature is opt-in.

If migrating from file-based instructions:

```bash
stigmem instruction migrate \
  --role engineer \
  --skill coding \
  --input ./instructions/ \
  --db stigmem.db
```

This converts markdown files into `instruction:content` facts and publishes a manifest. The 5-stage deprecation path ensures no instruction loss:

1. **Shadow** — instructions loaded from both file and stigmem; mismatches logged.
2. **Flip** — primary source switches to stigmem; file is fallback.
3. **File-off** — file loading disabled; stigmem-only.
4. **Cleanup** — file removed from deployment.
5. **Archive** — original files preserved in audit storage.

### Rollback

Set `STIGMEM_LAZY_INSTRUCTIONS=false` to revert to file-based loading.

---

## Security hardening (§22)

### Breaking changes

| Change | Impact | Action required |
|--------|--------|-----------------|
| mTLS required for federation | Plaintext federation connections rejected | Provision node certificates |
| TLS 1.3 floor enforced | TLS 1.2 connections refused | Verify your TLS stack supports 1.3 |
| Audit log mandatory | 13 event types must be emitted | Ensure audit storage is provisioned |
| Per-principal quotas active | Excessive writes receive HTTP 429 | Review default quota ceilings |
| Replay protection (±5 min window) | Requests with stale nonces rejected | Ensure node clocks are NTP-synced |

### Migration steps

1. **Provision mTLS certificates:**

```bash
# Using cert-manager (Kubernetes)
# Or manually:
stigmem cert generate \
  --entity-uri "stigmem://your-org/node-1" \
  --out /etc/stigmem/tls/
```

2. **Configure the audit log backend:**

```bash
export STIGMEM_AUDIT_LOG_PATH=/var/log/stigmem/audit.jsonl
# Or for external SIEM:
export STIGMEM_AUDIT_LOG_BACKEND=syslog
```

3. **Review quota defaults** (adjust if your workload exceeds these):

| Dimension | Default ceiling (per principal per minute) |
|-----------|--------------------------------------------|
| `fact_write` | 100 |
| `fact_read` | 1000 |
| `token_issue` | 10 |
| `recall` | 200 |
| `graph_query` | 200 |
| `subscription_create` | 10 |
| `admin_action` | 50 |

4. **Sync clocks** — replay protection uses a ±5-minute window:

```bash
# Verify NTP sync
timedatectl status | grep "synchronized"
```

### Key rotation

Ed25519 signing keys SHOULD be rotated every 90 days (capability issuer) or 365 days (node signing). The dual-trust period covers the 90-day maximum token lifetime:

```bash
stigmem key rotate --entity-uri "stigmem://your-org/node-1"
```

### Rollback

mTLS cannot be disabled without disconnecting from v2.0 peers. Audit logging and quotas can be disabled with `STIGMEM_AUDIT_ENABLED=false` and `STIGMEM_QUOTAS_ENABLED=false` respectively, but this violates the v2.0 spec.

---

## RTBF / tombstones (§23)

### Breaking changes

| Change | Impact | Action required |
|--------|--------|-----------------|
| `POST /v1/tombstones` endpoint | Admin-only; issues signed tombstone records | Grant admin keys to compliance operators |
| Recall-time filter active | Tombstoned entities excluded from all recall and graph results | No action — automatic |
| Federation tombstone route | Peers poll `GET /v1/federation/tombstones` every 5 minutes | Issue `tombstone:read` capability tokens to peers |
| Memory card suppression | Cards about tombstoned entities fully suppressed | No action — automatic |

### Migration steps

1. **Apply migration 013a** (automatic on startup).

2. **Issue tombstone:read tokens** for federation peers:

```python
resp = httpx.post("http://localhost:8787/v1/federation/tokens", json={
    "subject": "stigmem://peer-org/node-1",
    "verb": "tombstone:read",
    "object": "*",
})
```

3. **Test the tombstone flow:**

```bash
# Issue a tombstone (admin key required)
curl -X POST http://localhost:8787/v1/tombstones \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_uri": "user:test-entity", "scope": "*", "reason": "test"}'

# Verify recall excludes the entity
curl "http://localhost:8787/v1/recall?intent=test-entity&scope=company" \
  -H "Authorization: Bearer $AGENT_KEY"
# Should return no facts about "user:test-entity"
```

### Tombstone signing

Tombstones use RFC 8785 (JCS) canonical JSON with `"signature"` and `"reason"` fields excluded before canonicalization. The `key_id` field identifies the signing key without trial-verification.

### Rollback

Dropping the `tombstones` table removes all RTBF suppression. Previously tombstoned entities will reappear in recall results. This may violate compliance obligations.

---

## Time-travel / as-of queries (§24)

### Breaking changes

| Change | Impact | Action required |
|--------|--------|-----------------|
| `as_of` parameter on `/v1/recall` and `/v1/facts` | Returns historical knowledge-graph state | No action — opt-in per query |
| `fact_retractions` log (migration 013c) | Retraction writes now insert into append-only log | Verify no tooling depends on `confidence = 0.0` being the sole retraction signal |
| Legal-hold tombstones | `legal_hold: true` preserves facts for admin `as_of` queries | Understand the distinction for compliance |

### Migration steps

1. **Apply migration 013c** (automatic on startup).

2. **Use time-travel queries** for auditing:

```python
# What did we know about Alice on Jan 1, 2025?
resp = httpx.post("http://localhost:8787/v1/recall", json={
    "intent": "Alice preferences",
    "as_of": "2025-01-01T00:00:00Z",
    "scope": "company",
})
```

3. **Understand tombstone interaction:**
   - `legal_hold: false` (default) — entity is suppressed from ALL queries including historical.
   - `legal_hold: true` — entity is suppressed from live queries but visible in `as_of` queries for admin keys only.

### Rollback

Time-travel is a read-only feature. Dropping the `fact_retractions` table disables it without affecting live queries.

---

## Content-addressed fact IDs (§25)

### Breaking changes

| Change | Impact | Action required |
|--------|--------|-----------------|
| `cid` field on all new facts | All writes produce a `sha256:` CID alongside the UUID `fact_id` | No action — automatic |
| Dual-addressing during 12-month migration window | APIs accept both `fact_id` and `cid` as identifiers | Update clients to prefer CID addressing |
| Federation tamper detection | Inbound facts with mismatched CID are rejected | Ensure all peers are on v2.0 |
| `v1_1_ga_at` federation envelope field | Peers reject `cid: null` for facts created after GA | Coordinate upgrade timing with peers |

### Migration steps

1. **Apply migration 013b** (automatic on startup).

2. **Run the CID backfill** for existing facts:

```bash
stigmem backfill-cids --batch-size 1000 --rate-limit 500
```

3. **Monitor progress:**

```bash
curl http://localhost:8787/v1/admin/cid-backfill/status \
  -H "Authorization: Bearer $ADMIN_KEY"
# {"total_facts": 12340, "backfilled_facts": 8000, "remaining_facts": 4340, ...}
```

4. **Verify integrity** on a sample:

```bash
curl -X POST http://localhost:8787/v1/facts/fact_01J.../verify-cid \
  -H "Authorization: Bearer $AGENT_KEY"
# {"cid_valid": true, "computed_cid": "sha256:...", "stored_cid": "sha256:..."}
```

### CID format

```
CID = "sha256:" + hex_lowercase(SHA-256(RFC8785(canonical_body)))
```

The canonical body includes exactly six fields: `entity`, `relation`, `value`, `scope`, `source`, `confidence` — in lexicographic key order per RFC 8785.

### Rollback

The `cid` column and `fact_cid_aliases` table can be dropped. Facts revert to UUID-only addressing. Federation peers on v2.0 will reject facts without CIDs for post-GA timestamps.

---

## Environment variable summary (new in v2.0)

| Variable | Default | Section |
|----------|---------|---------|
| `STIGMEM_FEDERATION_TRUST_MODE` | `relaxed` | §19 |
| `STIGMEM_EMBED_PROVIDER` | `ollama` | §20 |
| `STIGMEM_EMBED_MODEL` | `nomic-embed-text` | §20 |
| `STIGMEM_EMBED_DIMENSIONS` | `768` | §20 |
| `STIGMEM_CARD_MAX_AGE_S` | `86400` | §20 |
| `STIGMEM_SUBSCRIPTION_REPLAY_S` | `3600` | §20 |
| `STIGMEM_LAZY_INSTRUCTIONS` | `true` | §21 |
| `STIGMEM_AUDIT_LOG_PATH` | `stderr` | §22 |
| `STIGMEM_AUDIT_ENABLED` | `true` | §22 |
| `STIGMEM_QUOTAS_ENABLED` | `true` | §22 |
| `STIGMEM_REPLAY_WINDOW_S` | `300` | §22 |
| `STIGMEM_TOMBSTONE_CACHE_TTL_S` | `60` | §23 |
| `STIGMEM_CID_BACKFILL_BATCH` | `1000` | §25 |
| `STIGMEM_MTLS_REQUIRED` | `false` | §22.1 — set `true` when a reverse proxy terminates TLS |
| `STIGMEM_TRUST_CACHE_BACKEND` | `memory` | §19.4 — set `redis` for multi-worker deployments |
| `STIGMEM_REDIS_URL` | _(none)_ | §19.4 — required when `STIGMEM_TRUST_CACHE_BACKEND=redis` |
| `STIGMEM_REQUIRE_CID` | `false` | §25 — set `true` to reject CID-less facts from upgraded peers |

---

## Pre-upgrade checklist

- [ ] Back up your database.
- [ ] Verify NTP clock sync on all nodes (±5 min tolerance for replay protection).
- [ ] Ensure Ollama or alternative embedding provider is available.
- [ ] Provision mTLS certificates for each federation peer.
- [ ] Generate Ed25519 keypair and prepare org manifest content.
- [ ] Coordinate upgrade timing with federation peers (mixed v1/v2 federation is not supported).
- [ ] Plan for initial embedding backfill time (proportional to fact count).
- [ ] Allocate admin API keys for compliance operators (tombstone management).

---

## Getting help

- [Spec v2.0 (full text)](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/docs/spec)
- [Operator runbooks](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/docs/operators/runbooks/deploy-runbooks)
- [Security hardening guide](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/docs/security/container-hardening)
- [API reference](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/docs/reference/api)
