---
title: Project Resources
sidebar_label: Project Resources
description: Open roles and community engagement paths for the Stigmem project — how to join the team or contribute.
---

# Project Resources

*Audience: potential contributors, engineers, security researchers, applied researchers.*

---

The Stigmem project is growing its team. The three roles below are open now and feed directly into the pre-reset attestation-chain work–14 build plan. They work alongside the existing engineering and documentation staff on the reference node, the spec, and the adapter ecosystem.

If you are interested in any of these roles, see [How to engage](#how-to-engage) below.

---

## Open roles

### Senior Engineer — Federation & Distributed Systems

**Needed for: the pre-reset attestation-chain work (Trust & Persistence Foundation) — shipped**

This is the highest-priority hire — the work starts immediately. the pre-reset attestation-chain work adds a federation trust architecture (spec §19 — org manifests, cross-org capability tokens, source-trust scores, quarantine garden behavior) and a multi-backend storage adapter (libSQL, Postgres, SQLCipher). The work is protocol-level distributed systems: signing schemes, HLC cursor semantics, replication under partition, and conflict resolution.

**What you'll work on:**

- Spec §19 Federation Trust draft and reference implementation.
- `StorageBackend` adapter trait; libSQL and Postgres adapters.
- Signed-snapshot backup and restore with point-in-time recovery.
- Federation replay-protection fuzz tests and pre-reset hardening mTLS / cert-pinning work.
- Conformance test suite (the pre-reset multi-backend work) — verifying backend parity across SQLite, libSQL, and Postgres.

**Background that fits:**

- Distributed systems fundamentals: consensus, replication, CRDTs, or comparable.
- Experience with federation protocols (ActivityPub, Matrix, XMPP, or equivalents) is useful but not required.
- Comfort reading and writing protocol specs alongside implementation.
- Python / FastAPI and TypeScript familiarity.

---

### Security Engineer

**Needed for: pre-reset hardening (Security Hardening) — shipped**

pre-reset hardening is a hardening phase: mTLS federation, API-key rotation enforcement, per-principal rate limits, container hardening, constant-time crypto audit, and community pen-test coordination. The Security Engineer role feeds the design of spec §19 (federation trust model) from the pre-reset attestation-chain work onward and owns pre-reset hardening delivery.

**What you'll work on:**

- Threat model documentation and the pre-reset hardening work (carried forward to v0.9.0a1) checklist.
- mTLS implementation for the federation peer protocol; cert-pinning option.
- Constant-time crypto audit of the Ed25519 signing and verification path.
- Transparency log integration (Rekor / Sigstore-equivalent for org-manifest rotation events per §19).
- Community pen-test coordination — scope, safe-harbor, and engagement path are already started at [Security & Pen Testing](./security-disclosure.md).
- the pre-reset design window right-to-be-forgotten tombstone design (cryptographic proof, cross-federation propagation).

**Background that fits:**

- Applied cryptography: signing, key management, mTLS, zero-trust.
- Familiarity with OWASP, CVSS, and responsible-disclosure processes.
- Experience hardening Python or Go services; container hardening background useful.
- Comfort with federated identity: SPIFFE/SPIRE, OAuth 2.0, Ed25519, transparency logs.

---

### Science / Research Agent — Graph Theory & Memory Structures

**Needed for: pre-reset graph & recall design (Graph Memory & Recall) — shipped**

pre-reset graph & recall design adds a graph adjacency index, vector embeddings, and a `recall` endpoint that serves salience-ranked, budget-bounded memory slices to agents. The research dimension is ongoing: what graph representations, recall algorithms, and memory structures make Stigmem more useful as a cognitive substrate?

This role thinks through emerging theory and surfaces capabilities the project can incorporate — graph embeddings, hypergraphs, sheaf theory for federated consistency, neural-symbolic recall, temporal knowledge graphs — and translates theoretical capability into spec proposals and testable prototypes.

**What you'll work on:**

- Graph adjacency index design and the pre-reset graph & recall design `recall` endpoint architecture.
- Salience-ranking model for the `recall` endpoint (combining recency, access frequency, vector similarity, and source-trust score).
- Ongoing literature review: higher-order graph embeddings, hypergraphs, sheaf-theoretic approaches to federated consistency, neural-symbolic retrieval, temporal knowledge graphs.
- Spec §20 "Recall & Graph" proposals.
- the pre-reset design window eval harness design — adversarial fact injection, recall accuracy benchmarks, comparative analysis across retrieval approaches.

**Background that fits:**

- Graph theory, information retrieval, or knowledge representation background.
- Familiarity with vector embedding models, approximate nearest-neighbor search, or knowledge graph systems.
- Comfort bridging theoretical capability to engineering constraints (spec proposals, prototype implementations).
- Python scientific stack: NumPy, networkx, sentence-transformers, or comparable.

---

## How to engage

All three roles are open now.

**To express interest:**

1. Open a [GitHub Discussion](https://github.com/eidetic-labs/stigmem/discussions) in the Stigmem repository with the role name in the title and a short description of your background and what draws you to the work.
2. Alternatively, open a GitHub Issue with a `[role inquiry]` prefix if you prefer a more structured format.

There is no formal application form or résumé-screening process. The team reviews all inquiries and responds within a few days.

---

## Other ways to contribute

If you want to contribute without a formal role commitment:

- **Code and spec contributions** — see [`CONTRIBUTING.md`](https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md) for the RFC process, conformance suite contribution guide, and prototype guidelines. Spec changes go through an open comment period before merging.
- **Security research** — see [Security & Pen Testing](./security-disclosure.md) for scope, safe-harbor terms, and how to report findings.
- **Spec review** — open issues or discussions on spec drafts in `stigmem/spec/`. Wire-format, namespace, and federation-semantics discussions are always open.
- **Adapter development** — build a Stigmem adapter for a tool or platform and open a PR. The Adapter ABI (spec §12) is normative; third-party adapters that pass the conformance suite are listed in the docs.

---

## Community norms

Stigmem is an open protocol project. All contributors and collaborators are expected to follow the [Code of Conduct](https://github.com/eidetic-labs/stigmem/blob/main/CODE_OF_CONDUCT.md).

Key principles:
- **Spec changes go through the RFC process.** Wire format, namespace, and federation semantics changes require a community comment period before merging. See `CONTRIBUTING.md`.
- **Working code beats design documents.** Prototypes and conformance tests are more persuasive than spec prose.
- **Protocol-layer focus.** Stigmem does not endorse or compete with specific agent platforms, IDEs, or workflow tools. It provides the shared substrate; those surfaces build on top of it.
