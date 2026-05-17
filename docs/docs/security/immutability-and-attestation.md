---
title: Immutability and Attestation
sidebar_label: Immutability & Attestation
description: Operator guide for the ADR-016 immutability stack, fact-chain checkpoints, and deployment hardening choices for admin-level storage tampering risk.
audience: Security
---

# Immutability and Attestation

**Audience:** operators, security engineers, and evaluators hardening a Stigmem node against storage-layer tampering.

Stigmem's R-23 risk is admin-level storage tampering: a privileged attacker with database access rewrites stored facts or security metadata below the HTTP/API layer. The mitigation is layered. Each layer catches a different failure mode, and operators get the strongest posture by enabling external attestations and storing evidence outside the mutable node.

---

## Control Stack

| Layer | Control | What it detects or prevents |
|---|---|---|
| L1 | Append-only fact journal plus projection tables | Normal write paths preserve insertion evidence and derive mutable read state from projections |
| L2 | SQLite trigger enforcement | Direct `UPDATE`/`DELETE` attempts on `facts` are rejected and recorded as `fact_mutation_attempted` audit evidence |
| L3 | Content-addressed fact IDs | Fact-body rewrites produce `cid_mismatch` on direct reads, queries, and recall hydration |
| L4 | Local fact hash chain | Removed, reordered, or rewritten local inserts break sequence/link verification |
| L5 | Transparency-log checkpoints | Chain heads are periodically anchored outside the mutable node through the configured transparency-log backend |
| Client/peer | Verification helpers and inbound checks | Clients and federation peers can reject mismatched CIDs and compact proof metadata |

The stack is defense in depth. CIDs catch body tampering; the local chain catches sequence and removal tampering; checkpoints make the chain head externally accountable; client/peer verification prevents a consumer from silently accepting bad proof material.

---

## Runtime Configuration

Use a transparency-log backend for production attestations:

```bash
STIGMEM_TL_BACKEND=rekor
STIGMEM_TL_REKOR_URL=https://rekor.sigstore.dev
```

For disconnected test environments, use the local append-only log backend and put the log on storage that ordinary node processes cannot rewrite:

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

If Rekor is unavailable, writes proceed and checkpoints remain pending for retry. Follow [Rekor unavailable response](../operators/runbooks/r-rekor-unavailable.md) if pending checkpoints accumulate.

---

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

Python clients can fail closed on CID or compact chain-proof mismatches:

```python
from stigmem import StigmemClient, verify_fact_chain_proof, verify_fact_cid

client = StigmemClient(url="https://your-node.example.com", api_key="sk-...")
result = client.recall("project status", scope="company", verify_full=True)

for scored in result.facts:
    verify_fact_cid(scored.fact)
verify_fact_chain_proof(result.chain_proof, require_checkpoint=True)
```

Federation pulls request full verification metadata and reject inbound facts when a supplied CID does not match the canonical fact body. Rejections emit `federation_integrity_rejected` evidence.

---

## WORM Storage

For high-assurance deployments, export evidence to write-once-read-many storage:

- Ship `fact_audit_log` and `federation_audit` rows to object storage with retention lock.
- Store local transparency-log files on immutable storage if `STIGMEM_TL_BACKEND=local`.
- Preserve database snapshots with signed manifests and retention policies. See [Backup & Restore](../operators/runbooks/backup-restore.md).
- Keep Rekor checkpoint metadata with your incident timeline so a restored node can be compared against the external chain head.

WORM storage does not replace Rekor or CID verification. It protects operational evidence when the node host itself is under administrator control.

---

## TEE Deployment Option

A trusted execution environment can reduce the blast radius of a compromised host administrator:

- Run the Stigmem node inside a TEE-capable runtime when available.
- Pin container images by digest and verify SBOM/provenance before deployment.
- Seal transparency-log credentials and node private keys to the measured runtime.
- Emit remote-attestation evidence to the same audit destination used for fact-chain checkpoints.

TEE deployment is an additional assurance layer, not a protocol requirement. The default mitigation still depends on CIDs, local chain verification, external checkpoints, and client/peer rejection behavior.

---

## Operator Checklist

- [ ] Enable Rekor-backed transparency-log checkpoints or place the local TL file on immutable storage.
- [ ] Alert on sustained pending checkpoints.
- [ ] Export audit rows to immutable storage before local retention expiry.
- [ ] Exercise `Stigmem-Verify: full` recall and SDK verification in staging.
- [ ] Include CID mismatch, chain-proof mismatch, and Rekor-unavailable scenarios in incident drills.
- [ ] Review [Harden a Deployment](../operators/tutorial-hardening.md) and [Container Hardening](./container-hardening.md) before production rollout.
