---
title: Immutability and Attestation
sidebar_label: Immutability & Attestation
description: Operator guide for the ADR-016 immutability stack, fact-chain checkpoints, and deployment hardening choices for admin-level storage tampering risk.
audience: Security
---

# Immutability and Attestation

<p className="stigmem-meta"><span>4 min read</span><span>Operator · Security engineer · Evaluator</span><span>Per ADR-016</span></p>

<div className="stigmem-lead">

**What this page is**

Operator guide for hardening a Stigmem node against storage-layer
tampering. R-23 is admin-level storage tampering: a privileged
attacker with database access rewrites stored facts or security
metadata below the HTTP/API layer.

</div>

<div className="stigmem-keypoint">

**The mitigation is layered.**

Each layer catches a different failure mode. Operators get the
strongest posture by enabling external attestations and storing
evidence outside the mutable node.

</div>

## Control stack

<div className="stigmem-fields">

<div>
<dt>Layer</dt>
<dt><span className="stigmem-fields__type">Control</span></dt>
<dd>What it detects or prevents</dd>
</div>

<div>
<dt>L1</dt>
<dt><span className="stigmem-fields__type">append-only journal + projection tables</span></dt>
<dd>Normal write paths preserve insertion evidence; mutable read state is derived from projections.</dd>
</div>

<div>
<dt>L2</dt>
<dt><span className="stigmem-fields__type">SQLite trigger enforcement</span></dt>
<dd>Direct <code>UPDATE</code>/<code>DELETE</code> attempts on <code>facts</code> are rejected and recorded as <code>fact_mutation_attempted</code> audit evidence.</dd>
</div>

<div>
<dt>L3</dt>
<dt><span className="stigmem-fields__type">content-addressed fact IDs</span></dt>
<dd>Fact-body rewrites produce <code>cid_mismatch</code> on direct reads, queries, and recall hydration.</dd>
</div>

<div>
<dt>L4</dt>
<dt><span className="stigmem-fields__type">local fact hash chain</span></dt>
<dd>Removed, reordered, or rewritten local inserts break sequence/link verification.</dd>
</div>

<div>
<dt>L5</dt>
<dt><span className="stigmem-fields__type">transparency-log checkpoints</span></dt>
<dd>Chain heads are periodically anchored outside the mutable node through the configured transparency-log backend.</dd>
</div>

<div>
<dt>Client / peer</dt>
<dt><span className="stigmem-fields__type">verification helpers and inbound checks</span></dt>
<dd>Clients and federation peers can reject mismatched CIDs and compact proof metadata.</dd>
</div>

</div>

The stack is defense in depth. CIDs catch body tampering; the local
chain catches sequence and removal tampering; checkpoints make the
chain head externally accountable; client/peer verification prevents
a consumer from silently accepting bad proof material.

## Runtime configuration

Use a transparency-log backend for production attestations:

```bash
STIGMEM_TL_BACKEND=rekor
STIGMEM_TL_REKOR_URL=https://rekor.sigstore.dev
```

For disconnected test environments, use the local append-only log
backend and put the log on storage that ordinary node processes
cannot rewrite:

```bash
STIGMEM_TL_BACKEND=local
STIGMEM_TL_LOCAL_PATH=/var/lib/stigmem/stigmem_tl.jsonl
```

Fact-chain checkpoints are created on count or age cadence:

```bash
STIGMEM_FACT_CHAIN_CHECKPOINT_INTERVAL=1000
STIGMEM_FACT_CHAIN_CHECKPOINT_MAX_AGE_S=60
STIGMEM_FACT_CHAIN_CHECKPOINT_RETRY_S=60
```

If Rekor is unavailable, writes proceed and checkpoints remain pending
for retry. Follow
[Rekor unavailable response](../operators/runbooks/r-rekor-unavailable.md)
if pending checkpoints accumulate.

## Verification

Request full verification metadata on recall:

```bash
curl -s http://localhost:8000/v1/recall \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -H "Stigmem-Verify: full" \
  -H "Content-Type: application/json" \
  -d '{"query":"project status","scope":"company","token_budget":1000}' \
  | jq '.chain_proof'
```

Python clients can fail closed on CID or compact chain-proof
mismatches:

```python
from stigmem import StigmemClient, verify_fact_chain_proof, verify_fact_cid

client = StigmemClient(url="https://your-node.example.com", api_key="sk-...")
result = client.recall("project status", scope="company", verify_full=True)

for scored in result.facts:
    verify_fact_cid(scored.fact)
verify_fact_chain_proof(result.chain_proof, require_checkpoint=True)
```

Federation pulls request full verification metadata and reject inbound
facts when a supplied CID does not match the canonical fact body.
Rejections emit `federation_integrity_rejected` evidence.

## WORM storage

For high-assurance deployments, export evidence to write-once-read-many
storage.

<div className="stigmem-grid">

<div><h4>Audit rows to retention-locked object storage</h4><p>Ship <code>fact_audit_log</code> and <code>federation_audit</code> rows to object storage with retention lock.</p></div>
<div><h4>Local TL on immutable storage</h4><p>Store local transparency-log files on immutable storage if <code>STIGMEM_TL_BACKEND=local</code>.</p></div>
<div><h4>Signed database snapshots</h4><p>Preserve database snapshots with signed manifests and retention policies. See <a href="../operators/runbooks/backup-restore">Backup &amp; Restore</a>.</p></div>
<div><h4>Rekor checkpoint metadata</h4><p>Keep Rekor checkpoint metadata with your incident timeline so a restored node can be compared against the external chain head.</p></div>

</div>

<div className="stigmem-keypoint">

**WORM storage does not replace Rekor or CID verification.**

It protects operational evidence when the node host itself is under
administrator control.

</div>

## TEE deployment option

A trusted execution environment can reduce the blast radius of a
compromised host administrator.

<div className="stigmem-grid">

<div><h4>TEE-capable runtime</h4><p>Run the Stigmem node inside a TEE-capable runtime when available.</p></div>
<div><h4>Pin and verify images</h4><p>Pin container images by digest and verify SBOM/provenance before deployment.</p></div>
<div><h4>Seal credentials to measurement</h4><p>Seal transparency-log credentials and node private keys to the measured runtime.</p></div>
<div><h4>Emit attestation evidence</h4><p>Emit remote-attestation evidence to the same audit destination used for fact-chain checkpoints.</p></div>

</div>

TEE deployment is an additional assurance layer, not a protocol
requirement. The default mitigation still depends on CIDs, local
chain verification, external checkpoints, and client/peer rejection
behavior.

## Operator checklist

<ol className="stigmem-steps">
<li>Enable Rekor-backed transparency-log checkpoints or place the local TL file on immutable storage.</li>
<li>Alert on sustained pending checkpoints.</li>
<li>Export audit rows to immutable storage before local retention expiry.</li>
<li>Exercise <code>Stigmem-Verify: full</code> recall and SDK verification in staging.</li>
<li>Include CID mismatch, chain-proof mismatch, and Rekor-unavailable scenarios in incident drills.</li>
<li>Review <a href="../operators/tutorial-hardening">Harden a Deployment</a> and <a href="./container-hardening">Container Hardening</a> before production rollout.</li>
</ol>
