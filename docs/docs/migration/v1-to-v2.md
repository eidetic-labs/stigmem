---
title: Migrating from v1.x to v2.0
sidebar_label: v1.x → v2.0
description: "Step-by-step upgrade guide for Stigmem v1.x to v2.0 — federation trust, recall, lazy instructions, security hardening, RTBF, time-travel, CIDs."
audience: Operator
---

# Migrating from v1.x to v2.0

:::warning Retracted — neither v1.x nor v2.0 shipped publicly

Per [ADR-001](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/001-versioning.md), the canonical version line of stigmem begins at `v0.9.0a1` (2026-05-09). The version *markers* `v1.x` and `v2.0` referenced in this document labeled internal development checkpoints, not tagged public releases — there is no installed v1.x or v2.0 to migrate from. This document is preserved as historical record of an announced-but-withdrawn migration path.

:::

# Migrating from v1.x to v2.0

<p className="stigmem-meta"><span>10 min read</span><span>Operator</span><span>Archived migration</span></p>

<div className="stigmem-lead">

**What this document is**

Historical step-by-step upgrade guide for Stigmem v1.x to v2.0 —
federation trust, recall, lazy instructions, security hardening,
RTBF, time-travel, CIDs. Preserved as the record of an announced
but withdrawn migration path.

</div>

**Audience:** Operators and developers running a stigmem node on v1.0 or pre-reset draft who want to upgrade to v2.0.
**Spec reference:** v2.0 promotes §19–§25 from draft to normative. §1–§18 are unchanged.

:::caution Breaking changes
v2.0 introduces new database migrations, mandatory mTLS for federation, and new wire-format fields. Read the full guide before upgrading a production node.
:::

## Upgrade overview

<div className="stigmem-fields">

<div>
<dt>Area</dt>
<dt><span className="stigmem-fields__type">Spec</span></dt>
<dd>What changed</dd>
</div>

<div>
<dt>Federation trust</dt>
<dt><span className="stigmem-fields__type">§19</span></dt>
<dd>Org manifests, capability tokens, transparency log.</dd>
</div>

<div>
<dt>Recall & graph</dt>
<dt><span className="stigmem-fields__type">§20</span></dt>
<dd>Graph index, vector embeddings, hybrid recall, memory cards, subscriptions.</dd>
</div>

<div>
<dt>Lazy instructions</dt>
<dt><span className="stigmem-fields__type">§21</span></dt>
<dd>Boot stub, instruction manifest, <code>recall_instruction</code> tool.</dd>
</div>

<div>
<dt>Security hardening</dt>
<dt><span className="stigmem-fields__type">§22</span></dt>
<dd>mTLS, key rotation, audit log, quotas, replay protection.</dd>
</div>

<div>
<dt>RTBF tombstones</dt>
<dt><span className="stigmem-fields__type">§23</span></dt>
<dd>Tombstone records, recall-time filter, federation propagation.</dd>
</div>

<div>
<dt>Time-travel queries</dt>
<dt><span className="stigmem-fields__type">§24</span></dt>
<dd><code>as_of</code> parameter on recall and facts endpoints.</dd>
</div>

<div>
<dt>Content-addressed IDs</dt>
<dt><span className="stigmem-fields__type">§25</span></dt>
<dd>SHA-256 CIDs, dual addressing, federation tamper detection.</dd>
</div>

</div>

## Suggested cutover order

<ol className="stigmem-steps">
<li><strong>Security hardening (§22)</strong> — enable mTLS and audit logging first; all subsequent features depend on it.</li>
<li><strong>Federation trust (§19)</strong> — publish your org manifest and set up transparency log integration.</li>
<li><strong>Recall & graph (§20)</strong> — run the embedding backfill; enable the recall pipeline.</li>
<li><strong>Lazy instruction discovery (§21)</strong> — migrate instruction files if applicable.</li>
<li><strong>RTBF tombstones (§23)</strong> — enable the tombstone API and federation route.</li>
<li><strong>Time-travel queries (§24)</strong> — available immediately after §23 migrations.</li>
<li><strong>Content-addressed IDs (§25)</strong> — run <code>stigmem backfill-cids</code> last (non-blocking).</li>
</ol>

## Experimental features

<div className="stigmem-fields">

<div>
<dt>Feature</dt>
<dt><span className="stigmem-fields__type">Section · Risk</span></dt>
<dd>Constraint</dd>
</div>

<div>
<dt>Lazy Instruction Discovery</dt>
<dt><span className="stigmem-fields__type">§21 · prompt injection</span></dt>
<dd>Do not use for agents handling sensitive data or irreversible tool use until GA.</dd>
</div>

<div>
<dt>RTBF Tombstones</dt>
<dt><span className="stigmem-fields__type">§23 · federated erasure</span></dt>
<dd>Do not rely on tombstone federation for GDPR/CCPA in multi-node deployments.</dd>
</div>

<div>
<dt>Time-Travel Queries</dt>
<dt><span className="stigmem-fields__type">§24 · post-erased data</span></dt>
<dd>Test isolation behavior on your production backend before compliance use.</dd>
</div>

<div>
<dt>Content-Addressed Fact IDs</dt>
<dt><span className="stigmem-fields__type">§25 · CID-less accepted</span></dt>
<dd>Do not rely on CID as a security control in untrusted federation topologies.</dd>
</div>

</div>

## Operator warnings (GA features with non-obvious risks)

<div className="stigmem-fields">

<div>
<dt>Feature</dt>
<dt><span className="stigmem-fields__type">Risk</span></dt>
<dd>Required action</dd>
</div>

<div>
<dt>§22.1 mTLS</dt>
<dt><span className="stigmem-fields__type">silent plaintext fallback</span></dt>
<dd>Set <code>STIGMEM_MTLS_REQUIRED=true</code> in production.</dd>
</div>

<div>
<dt>§19.4 Source-trust cache</dt>
<dt><span className="stigmem-fields__type">per-worker incoherence</span></dt>
<dd>Set <code>STIGMEM_TRUST_CACHE_BACKEND=redis</code> for production multi-worker.</dd>
</div>

<div>
<dt>§6.7–§6.8 N-node backpressure</dt>
<dt><span className="stigmem-fields__type">draft spec</span></dt>
<dd>Test your topology in staging.</dd>
</div>

<div>
<dt>§19.5 Quarantine Garden</dt>
<dt><span className="stigmem-fields__type">silent data loss</span></dt>
<dd>Pre-create quarantine garden before enabling <code>trust_mode=strict</code>.</dd>
</div>

</div>

## Database migrations

<div className="stigmem-fields">

<div>
<dt>Migration</dt>
<dt><span className="stigmem-fields__type">Creates</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>013a</code></dt>
<dt><span className="stigmem-fields__type">tombstones, tombstone_revocations</span></dt>
<dd>RTBF tombstone storage (§23.5.3).</dd>
</div>

<div>
<dt><code>013b</code></dt>
<dt><span className="stigmem-fields__type">facts.cid, fact_cid_aliases</span></dt>
<dd>Content-addressed IDs (§25.3.1).</dd>
</div>

<div>
<dt><code>013c</code></dt>
<dt><span className="stigmem-fields__type">fact_retractions</span></dt>
<dd>Append-only retraction log for time-travel (§24.2.1).</dd>
</div>

</div>

```bash
# Docker Compose (recommended)
git pull
docker compose up --build -d

# Verify migrations
curl -s http://localhost:8787/v1/admin/status | jq '.migrations'
```

<div className="stigmem-keypoint">

**Rolling back after tombstones have been issued will lose RTBF compliance state.**

Take a backup before upgrading.

</div>

## Federation trust (§19)

<div className="stigmem-fields">

<div>
<dt>Breaking change</dt>
<dt><span className="stigmem-fields__type">Impact</span></dt>
<dd>Action required</dd>
</div>

<div>
<dt>Org manifest required</dt>
<dt><span className="stigmem-fields__type">connections rejected</span></dt>
<dd>Publish manifest at <code>/.well-known/stigmem-manifest.json</code>.</dd>
</div>

<div>
<dt>Capability tokens replace ad-hoc trust</dt>
<dt><span className="stigmem-fields__type">existing fail</span></dt>
<dd>Issue <code>federate</code> verb tokens for each peer.</dd>
</div>

<div>
<dt>Transparency log integration</dt>
<dt><span className="stigmem-fields__type">strict mode</span></dt>
<dd>Configure Rekor or self-hosted log.</dd>
</div>

<div>
<dt>90-day token expiry ceiling</dt>
<dt><span className="stigmem-fields__type">renewal cycle</span></dt>
<dd>Set up automated token renewal.</dd>
</div>

</div>

**Migration steps:**

<ol className="stigmem-steps">
<li><strong>Generate an Ed25519 keypair</strong> for your node: <code>stigmem keygen --out /etc/stigmem/node-key.pem</code></li>
<li><strong>Publish your org manifest:</strong> <code>stigmem manifest publish --entity-uri "stigmem://your-org/node-1" --key /etc/stigmem/node-key.pem</code></li>
<li><strong>Issue capability tokens</strong> for each federation peer via <code>POST /v1/federation/tokens</code>.</li>
<li><strong>Configure trust mode:</strong> <code>STIGMEM_FEDERATION_TRUST_MODE=strict</code> for production, <code>relaxed</code> for development.</li>
</ol>

## Recall & graph (§20)

<div className="stigmem-fields">

<div>
<dt>Breaking change</dt>
<dt><span className="stigmem-fields__type">Impact</span></dt>
<dd>Action required</dd>
</div>

<div>
<dt><code>entity_edges</code> materialized at startup</dt>
<dt><span className="stigmem-fields__type">first-boot rebuild</span></dt>
<dd>Allow extra startup time.</dd>
</div>

<div>
<dt>Embedding storage (<code>vec_facts</code>)</dt>
<dt><span className="stigmem-fields__type">nomic-embed-text default</span></dt>
<dd>Ensure Ollama is running or configure an alternative provider.</dd>
</div>

<div>
<dt><code>GET /v1/recall</code> replaces ad-hoc queries</dt>
<dt><span className="stigmem-fields__type">SDK update</span></dt>
<dd>Update SDK calls.</dd>
</div>

<div>
<dt>Graph depth capped at 3</dt>
<dt><span className="stigmem-fields__type">HTTP 400</span></dt>
<dd>Update any client code using deeper traversal.</dd>
</div>

</div>

```bash
# Default: Ollama with nomic-embed-text (local, Apache-2.0)
ollama pull nomic-embed-text

# Or use a cloud provider
export STIGMEM_EMBED_PROVIDER=openai
export STIGMEM_EMBED_MODEL=text-embedding-3-small
```

<div className="stigmem-keypoint">

**Allow time for initial embedding backfill.**

For large stores (100k+ facts), this may take several minutes.

</div>

## Lazy instruction discovery (§21)

If you are not using lazy instructions, no action is required — the feature is opt-in. If migrating from file-based instructions:

```bash
stigmem instruction migrate \
  --role engineer \
  --skill coding \
  --input ./instructions/ \
  --db stigmem.db
```

**5-stage deprecation path** ensures no instruction loss:

<ol className="stigmem-steps">
<li><strong>Shadow</strong> — instructions loaded from both file and stigmem; mismatches logged.</li>
<li><strong>Flip</strong> — primary source switches to stigmem; file is fallback.</li>
<li><strong>File-off</strong> — file loading disabled; stigmem-only.</li>
<li><strong>Cleanup</strong> — file removed from deployment.</li>
<li><strong>Archive</strong> — original files preserved in audit storage.</li>
</ol>

## Security hardening (§22)

<div className="stigmem-fields">

<div>
<dt>Breaking change</dt>
<dt><span className="stigmem-fields__type">Impact</span></dt>
<dd>Action required</dd>
</div>

<div>
<dt>mTLS required for federation</dt>
<dt><span className="stigmem-fields__type">plaintext rejected</span></dt>
<dd>Provision node certificates.</dd>
</div>

<div>
<dt>TLS 1.3 floor enforced</dt>
<dt><span className="stigmem-fields__type">TLS 1.2 refused</span></dt>
<dd>Verify your TLS stack supports 1.3.</dd>
</div>

<div>
<dt>Audit log mandatory</dt>
<dt><span className="stigmem-fields__type">14 event types</span></dt>
<dd>Ensure audit storage is provisioned.</dd>
</div>

<div>
<dt>Per-principal quotas active</dt>
<dt><span className="stigmem-fields__type">HTTP 429</span></dt>
<dd>Review default quota ceilings.</dd>
</div>

<div>
<dt>Replay protection (±5 min)</dt>
<dt><span className="stigmem-fields__type">stale nonces rejected</span></dt>
<dd>Ensure node clocks are NTP-synced.</dd>
</div>

</div>

**Default quotas (per principal per minute):**

<div className="stigmem-fields">

<div>
<dt>Dimension</dt>
<dt><span className="stigmem-fields__type">Ceiling</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>fact_write</code></dt>
<dt><span className="stigmem-fields__type">100</span></dt>
<dd>—</dd>
</div>

<div>
<dt><code>fact_read</code></dt>
<dt><span className="stigmem-fields__type">1000</span></dt>
<dd>—</dd>
</div>

<div>
<dt><code>token_issue</code></dt>
<dt><span className="stigmem-fields__type">10</span></dt>
<dd>—</dd>
</div>

<div>
<dt><code>recall</code></dt>
<dt><span className="stigmem-fields__type">200</span></dt>
<dd>—</dd>
</div>

<div>
<dt><code>graph_query</code></dt>
<dt><span className="stigmem-fields__type">200</span></dt>
<dd>—</dd>
</div>

<div>
<dt><code>subscription_create</code></dt>
<dt><span className="stigmem-fields__type">10</span></dt>
<dd>—</dd>
</div>

<div>
<dt><code>admin_action</code></dt>
<dt><span className="stigmem-fields__type">50</span></dt>
<dd>—</dd>
</div>

</div>

**Key rotation:** Ed25519 signing keys SHOULD be rotated every 90 days (capability issuer) or 365 days (node signing).

```bash
stigmem key rotate --entity-uri "stigmem://your-org/node-1"
```

## RTBF / tombstones (§23)

<div className="stigmem-fields">

<div>
<dt>Breaking change</dt>
<dt><span className="stigmem-fields__type">Impact</span></dt>
<dd>Action required</dd>
</div>

<div>
<dt><code>POST /v1/tombstones</code></dt>
<dt><span className="stigmem-fields__type">admin-only</span></dt>
<dd>Grant admin keys to compliance operators.</dd>
</div>

<div>
<dt>Recall-time filter active</dt>
<dt><span className="stigmem-fields__type">automatic</span></dt>
<dd>Tombstoned entities excluded from all recall and graph results.</dd>
</div>

<div>
<dt>Federation tombstone route</dt>
<dt><span className="stigmem-fields__type">5-min poll</span></dt>
<dd>Issue <code>tombstone:read</code> capability tokens to peers.</dd>
</div>

<div>
<dt>Memory card suppression</dt>
<dt><span className="stigmem-fields__type">automatic</span></dt>
<dd>Cards about tombstoned entities fully suppressed.</dd>
</div>

</div>

```bash
# Issue a tombstone (admin key required)
curl -X POST http://localhost:8787/v1/tombstones \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_uri": "user:test-entity", "scope": "*", "reason": "test"}'
```

<div className="stigmem-keypoint">

**Tombstones use RFC 8785 (JCS) canonical JSON.**

`"signature"` and `"reason"` fields are excluded before
canonicalization. The `key_id` field identifies the signing key
without trial-verification.

</div>

## Time-travel / as-of queries (§24)

```python
# What did we know about Alice on Jan 1, 2025?
resp = httpx.post("http://localhost:8787/v1/recall", json={
    "intent": "Alice preferences",
    "as_of": "2025-01-01T00:00:00Z",
    "scope": "company",
})
```

<div className="stigmem-keypoint">

**Tombstone interaction:**

- `legal_hold: false` (default) — entity is suppressed from ALL queries including historical.
- `legal_hold: true` — entity is suppressed from live queries but visible in `as_of` queries for admin keys only.

</div>

## Content-addressed fact IDs (§25)

<div className="stigmem-fields">

<div>
<dt>Breaking change</dt>
<dt><span className="stigmem-fields__type">Impact</span></dt>
<dd>Action required</dd>
</div>

<div>
<dt><code>cid</code> field on all new facts</dt>
<dt><span className="stigmem-fields__type">automatic</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Dual-addressing during 12-month window</dt>
<dt><span className="stigmem-fields__type">prefer CID</span></dt>
<dd>Update clients to prefer CID addressing.</dd>
</div>

<div>
<dt>Federation tamper detection</dt>
<dt><span className="stigmem-fields__type">mismatched CID rejected</span></dt>
<dd>Ensure all peers are on v2.0.</dd>
</div>

</div>

```bash
# Run CID backfill for existing facts
stigmem backfill-cids --batch-size 1000 --rate-limit 500

# Monitor progress
curl http://localhost:8787/v1/admin/cid-backfill/status \
  -H "Authorization: Bearer $ADMIN_KEY"

# Verify integrity on a sample
curl -X POST http://localhost:8787/v1/facts/fact_01J.../verify-cid \
  -H "Authorization: Bearer $AGENT_KEY"
```

**CID format:**

```
CID = "sha256:" + hex_lowercase(SHA-256(RFC8785(canonical_body)))
```

The canonical body includes exactly six fields: `entity`, `relation`, `value`, `scope`, `source`, `confidence` — in lexicographic key order per RFC 8785.

## Environment variable summary (new in v2.0)

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Section</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_TRUST_MODE</code></dt>
<dt><span className="stigmem-fields__type">relaxed</span></dt>
<dd>§19</dd>
</div>

<div>
<dt><code>STIGMEM_EMBED_PROVIDER</code> / <code>_MODEL</code> / <code>_DIMENSIONS</code></dt>
<dt><span className="stigmem-fields__type">ollama / nomic / 768</span></dt>
<dd>§20</dd>
</div>

<div>
<dt><code>STIGMEM_CARD_MAX_AGE_S</code></dt>
<dt><span className="stigmem-fields__type">86400</span></dt>
<dd>§20</dd>
</div>

<div>
<dt><code>STIGMEM_SUBSCRIPTION_REPLAY_S</code></dt>
<dt><span className="stigmem-fields__type">3600</span></dt>
<dd>§20</dd>
</div>

<div>
<dt><code>STIGMEM_LAZY_INSTRUCTIONS</code></dt>
<dt><span className="stigmem-fields__type">true</span></dt>
<dd>§21</dd>
</div>

<div>
<dt><code>STIGMEM_AUDIT_LOG_PATH</code> / <code>_ENABLED</code></dt>
<dt><span className="stigmem-fields__type">stderr / true</span></dt>
<dd>§22</dd>
</div>

<div>
<dt><code>STIGMEM_QUOTAS_ENABLED</code></dt>
<dt><span className="stigmem-fields__type">true</span></dt>
<dd>§22</dd>
</div>

<div>
<dt><code>STIGMEM_REPLAY_WINDOW_S</code></dt>
<dt><span className="stigmem-fields__type">300</span></dt>
<dd>§22</dd>
</div>

<div>
<dt><code>STIGMEM_TOMBSTONE_CACHE_TTL_S</code></dt>
<dt><span className="stigmem-fields__type">60</span></dt>
<dd>§23</dd>
</div>

<div>
<dt><code>STIGMEM_CID_BACKFILL_BATCH</code></dt>
<dt><span className="stigmem-fields__type">1000</span></dt>
<dd>§25</dd>
</div>

<div>
<dt><code>STIGMEM_MTLS_REQUIRED</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>§22.1 — set true behind reverse proxies.</dd>
</div>

<div>
<dt><code>STIGMEM_TRUST_CACHE_BACKEND</code></dt>
<dt><span className="stigmem-fields__type">memory</span></dt>
<dd>§19.4 — set <code>redis</code> for multi-worker.</dd>
</div>

<div>
<dt><code>STIGMEM_REDIS_URL</code></dt>
<dt><span className="stigmem-fields__type">none</span></dt>
<dd>§19.4 — required when trust cache is Redis.</dd>
</div>

<div>
<dt><code>STIGMEM_REQUIRE_CID</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>§25 — set true to reject CID-less facts.</dd>
</div>

</div>

## Pre-upgrade checklist

<ol className="stigmem-steps">
<li>Back up your database.</li>
<li>Verify NTP clock sync on all nodes (±5 min tolerance for replay protection).</li>
<li>Ensure Ollama or alternative embedding provider is available.</li>
<li>Provision mTLS certificates for each federation peer.</li>
<li>Generate Ed25519 keypair and prepare org manifest content.</li>
<li>Coordinate upgrade timing with federation peers (mixed v1/v2 federation is not supported).</li>
<li>Plan for initial embedding backfill time (proportional to fact count).</li>
<li>Allocate admin API keys for compliance operators (tombstone management).</li>
</ol>

## Getting help

<div className="stigmem-grid">

<div><h4><a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/docs/spec">Spec v2.0 (full text)</a></h4></div>
<div><h4><a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/docs/operators/runbooks/deploy-runbooks">Operator runbooks</a></h4></div>
<div><h4><a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/docs/security/container-hardening">Security hardening guide</a></h4></div>
<div><h4><a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/docs/reference/api">API reference</a></h4></div>

</div>
