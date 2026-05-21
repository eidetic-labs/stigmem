---
feature_id: content-addressed-ids
title: Content-addressed fact IDs
status: active
stability: stable
since: 0.9.0a1
owner: maintainers
feature_type: core
default_surface: default
canonical_spec: Spec-21-Content-Addressed-IDs
implementation_path: node/src/stigmem_node/cid.py
package: stigmem-node
adr_refs:
  - ADR-016
  - ADR-017
  - ADR-020
security_refs:
  - R-18
release_lines:
  - v0.9.0a1
  - v0.9.0a3
---

# Content-Addressed Fact IDs

Content-addressed fact IDs, or CIDs, are the core Stigmem identifier and
integrity feature for facts. A CID is recomputed from a fact's canonical body
and stored with the fact so reads, recall hydration, federation, and operator
verification can detect tampering or canonicalization drift.

CIDs are core behavior per ADR-017. They are not an experimental plugin and no
`stigmem-plugin-cids` package is planned.

## Current State

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `stable` |
| Default surface | `default` |
| Primary implementation | `node/src/stigmem_node/cid.py` |
| Primary package | `stigmem-node` |
| Canonical spec | `Spec-21-Content-Addressed-IDs` |

## Implementation Surface

| Surface | Path | Notes |
| --- | --- | --- |
| CID computation and validation | `node/src/stigmem_node/cid.py` | Computes `sha256:` CIDs from canonical fact bodies and verifies stored rows. |
| Fact write/read integration | `node/src/stigmem_node/routes/facts/` | Persists CIDs, resolves facts by CID, and rejects read-path CID mismatches. |
| CID verification route | `node/src/stigmem_node/routes/facts/cid.py` | Exposes `POST /v1/facts/{fact_id}/verify-cid`. |
| Backfill status route | `node/src/stigmem_node/routes/cid_admin.py` | Exposes `GET /v1/admin/cid-backfill/status`. |
| SDK verification helpers | `sdks/stigmem-py/src/stigmem/verification.py` | Recomputes and verifies fact CIDs for clients. |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
